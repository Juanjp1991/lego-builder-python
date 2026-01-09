"""Control Flow Agent module.

This module defines the ControlFlowAgent, which orchestrates the interaction
between the Designer and Coder agents to generate and modify 3D models.
"""

import re
import json
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any, List
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.genai.types import Content, Part

import logging
from sub_agents.designer.agent import get_designer_agent, get_designer_verification_agent
from sub_agents.coder.agent import get_coder_agent, CodeModifier
from tools.renderer import render_stl, render_stl_async
from tools.cad_tools import create_cad_model
from validation.buildability import validate_buildability, BuildabilityResult, BrickPlacement
from a2a.models import GenerateOptions
from utils.timing import TimingCollector, get_timing_collector, reset_timing_collector

logger = logging.getLogger(__name__)

# Minimum buildability score threshold for auto-correction
BUILDABILITY_THRESHOLD = 70

# High buildability threshold to skip Designer verification
HIGH_BUILDABILITY_SKIP_THRESHOLD = 90

class ControlFlowAgent:
    """Orchestrates the multi-agent workflow for 3D model generation and modification.

    Attributes:
        app_name (str): The name of the application.
        session_service: Service for managing user sessions.
        memory_service: Service for managing agent memory.
        designer_agent: The initialized Designer Agent.
        coder_agent: The initialized Coder Agent.
        code_modifier: The CodeModifier instance for handling modifications.
    """

    def __init__(self, session_service: InMemorySessionService, memory_service: InMemoryMemoryService):
        """Initializes the ControlFlowAgent.

        Args:
            session_service (InMemorySessionService): Service for managing user sessions.
            memory_service (InMemoryMemoryService): Service for managing agent memory.
        """
        self.app_name = "forma-ai-service"
        self.session_service = session_service
        self.memory_service = memory_service

        # Initialize sub-agents
        self.designer_agent = get_designer_agent()
        self.designer_verification_agent = get_designer_verification_agent()  # Lighter Flash model
        self.coder_agent = get_coder_agent()
        self.code_modifier = CodeModifier()

        # Store latest buildability result for response inclusion
        self._last_buildability_result: Optional[BuildabilityResult] = None
        
        # Timing collector for current request
        self._timing: Optional[TimingCollector] = None

    async def _ensure_session(self, session_id: str, user_id: str) -> None:
        """Ensures a session exists for the user.

        Args:
            session_id (str): The unique identifier for the session.
            user_id (str): The unique identifier for the user.
        """
        logger.info(f"ControlFlow: Ensuring session {session_id} exists for user {user_id}")
        session = await self.session_service.get_session(app_name=self.app_name, user_id=user_id, session_id=session_id)
        if not session:
            logger.info(f"ControlFlow: Session not found. Creating new session...")
            await self.session_service.create_session(app_name=self.app_name, user_id=user_id, session_id=session_id)
            logger.info("ControlFlow: Session created.")
        else:
            logger.info("ControlFlow: Session found.")

    async def _run_designer_step(self, prompt: str, user_id: str, session_id: str) -> str:
        """Runs the Designer Agent to generate a specification.

        Args:
            prompt (str): The user's initial request.
            user_id (str): The unique identifier for the user.
            session_id (str): The unique identifier for the session.

        Returns:
            str: The generated design specification as a string.
        """
        logger.info("--- Running Designer Agent ---")
        designer_runner = Runner(
            agent=self.designer_agent,
            app_name=self.app_name,
            session_service=self.session_service,
            memory_service=self.memory_service
        )
        
        designer_input = Content(parts=[Part(text=prompt)], role="user")
        designer_output = ""
        
        async for event in designer_runner.run_async(user_id=user_id, session_id=session_id, new_message=designer_input):
            if event.is_final_response() and event.content and event.content.parts:
                designer_output = event.content.parts[0].text
                logger.info(f"ControlFlow: Designer Agent Output:\n{designer_output}")
        
        return designer_output

    async def _run_coder_step(self, spec: str, user_id: str, session_id: str, result_container: dict[str, str]) -> AsyncGenerator[str, None]:
        """Runs the Coder Agent to generate code.

        Args:
            spec (str): The design specification.
            user_id (str): The unique identifier for the user.
            session_id (str): The unique identifier for the session.
            result_container (dict[str, str]): A dictionary to store the full output string.

        Yields:
            str: Chunks of the generated text output.
        """
        coder_runner = Runner(
            agent=self.coder_agent,
            app_name=self.app_name,
            session_service=self.session_service,
            memory_service=self.memory_service
        )
        
        coder_input = Content(parts=[Part(text=f"Specification:\n{spec}")], role="user")
        coder_output = ""
        
        async for event in coder_runner.run_async(user_id=user_id, session_id=session_id, new_message=coder_input):
            if event.content:
                 tool_output = self._parse_tool_output(event.content)
                 if tool_output:
                     coder_output += f"\nTool Output: {tool_output}"
            
            if event.is_final_response() and event.content and event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                if text_parts:
                    chunk = "\n" + "\n".join(text_parts)
                    coder_output += chunk
                    yield "\n".join(text_parts)
        
        result_container["output"] = coder_output
        logger.info(f"ControlFlow: Coder Output Raw: {coder_output}")

    def _parse_tool_output(self, content: Content) -> str | None:
        """Parses tool output from the content."""
        for part in content.parts:
            if part.function_response:
                return part.function_response.response
        return None

    def _generate_synthetic_build_sequence(self, prompt: str) -> List[BrickPlacement]:
        """Generate a synthetic colored build_sequence based on the prompt.
        
        This is a fallback when the Coder agent doesn't output build_sequence metadata.
        It creates a simple brick layout with colors derived from prompt keywords.
        
        Args:
            prompt: The original user/design prompt
            
        Returns:
            List of BrickPlacement objects with colors
        """
        prompt_lower = prompt.lower()
        
        # Determine primary and secondary colors based on prompt keywords
        if any(word in prompt_lower for word in ["tree", "plant", "forest", "leaf"]):
            colors = ["green", "brown", "green", "green", "brown"]
        elif any(word in prompt_lower for word in ["bear", "teddy", "animal"]):
            colors = ["brown", "tan", "brown", "black", "brown"]
        elif any(word in prompt_lower for word in ["car", "vehicle", "truck"]):
            colors = ["red", "black", "gray", "red", "black"]
        elif any(word in prompt_lower for word in ["plane", "airplane", "aircraft"]):
            colors = ["white", "blue", "white", "gray", "blue"]
        elif any(word in prompt_lower for word in ["house", "building", "home"]):
            colors = ["red", "white", "red", "gray", "brown"]
        elif any(word in prompt_lower for word in ["robot", "machine"]):
            colors = ["gray", "blue", "gray", "black", "yellow"]
        else:
            # Default colorful pattern
            colors = ["red", "blue", "yellow", "green", "white"]
        
        # Generate a simple 3-layer brick structure
        bricks = []
        step = 1
        
        # Layer 1 (base) - 2x4 bricks
        for x in range(0, 32, 16):
            for y in range(0, 32, 8):
                bricks.append(BrickPlacement(
                    step=step,
                    brick="2x4",
                    color=colors[step % len(colors)],
                    position={"x": float(x), "y": float(y), "z": 0.0}
                ))
                step += 1
        
        # Layer 2 (middle) - staggered 2x4
        for x in range(8, 24, 16):
            for y in range(0, 32, 8):
                bricks.append(BrickPlacement(
                    step=step,
                    brick="2x4",
                    color=colors[step % len(colors)],
                    position={"x": float(x), "y": float(y), "z": 9.6}
                ))
                step += 1
        
        # Layer 3 (top) - 2x2 accent bricks
        for x in range(0, 32, 16):
            for y in range(8, 24, 16):
                bricks.append(BrickPlacement(
                    step=step,
                    brick="2x2",
                    color=colors[(step + 1) % len(colors)],
                    position={"x": float(x), "y": float(y), "z": 19.2}
                ))
                step += 1
        
        logger.info(f"ControlFlow: Generated {len(bricks)} synthetic bricks with colors based on prompt")
        return bricks

    def _extract_model_metadata(self, coder_output: str) -> Dict[str, Any]:
        """Extract model metadata (build_sequence, layers, etc.) from coder output.

        The coder is instructed to output these variables in JSON format.

        Args:
            coder_output (str): The full text output from the Coder Agent.

        Returns:
            Dict containing build_sequence, layers, brick_count, layer_count
        """
        metadata = {
            "build_sequence": [],
            "layers": [],
            "brick_count": 0,
            "layer_count": 0
        }

        # Try to find JSON metadata in the output
        # Look for patterns like build_sequence = [...] or metadata_json = {...}
        json_patterns = [
            r'build_sequence\s*=\s*(\[[\s\S]*?\])',
            r'layers\s*=\s*(\[[\s\S]*?\])',
            r'"build_sequence"\s*:\s*(\[[\s\S]*?\])',
            r'metadata\s*=\s*(\{[\s\S]*?\})',
        ]

        for pattern in json_patterns:
            match = re.search(pattern, coder_output)
            if match:
                try:
                    # Try to parse as JSON (handle Python-style to JSON conversion)
                    json_str = match.group(1).replace("'", '"').replace("True", "true").replace("False", "false")
                    data = json.loads(json_str)

                    if "build_sequence" in pattern:
                        metadata["build_sequence"] = data
                        metadata["brick_count"] = len(data)
                    elif "layers" in pattern:
                        metadata["layers"] = data
                        metadata["layer_count"] = len(data)
                    elif "metadata" in pattern and isinstance(data, dict):
                        metadata.update(data)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse metadata JSON: {e}")

        # Infer layer count from build_sequence if not set
        if metadata["build_sequence"] and not metadata["layer_count"]:
            z_positions = set()
            for brick in metadata["build_sequence"]:
                if isinstance(brick, dict) and "position" in brick:
                    z = brick["position"].get("z", 0)
                    layer = int(round(z / 9.6))  # LEGO brick height
                    z_positions.add(layer)
            metadata["layer_count"] = len(z_positions)

        return metadata

    def _validate_and_maybe_correct(
        self,
        model_data: Dict[str, Any],
        coder_output: str,
        original_spec: str
    ) -> tuple[BuildabilityResult, bool]:
        """Validate buildability and determine if self-correction is needed.

        Args:
            model_data: The extracted model metadata
            coder_output: The raw coder output
            original_spec: The original design specification

        Returns:
            Tuple of (BuildabilityResult, needs_correction: bool)
        """
        result = validate_buildability(model_data)
        self._last_buildability_result = result

        logger.info(f"Buildability validation: score={result.score}, valid={result.valid}, "
                   f"issues={len(result.issues)}")

        needs_correction = result.score < BUILDABILITY_THRESHOLD
        return result, needs_correction

    def _build_correction_prompt(
        self,
        original_spec: str,
        validation_result: BuildabilityResult
    ) -> str:
        """Build a prompt for the coder to correct buildability issues.

        Args:
            original_spec: The original design specification
            validation_result: The buildability validation result

        Returns:
            A prompt string for the coder to fix the issues
        """
        issues_text = "\n".join(f"- {issue}" for issue in validation_result.issues)
        recommendations_text = "\n".join(f"- {rec}" for rec in validation_result.recommendations)

        return f"""Original Specification:
{original_spec}

BUILDABILITY VALIDATION FAILED (Score: {validation_result.score}/100)

Issues Found:
{issues_text if issues_text else "- No specific issues"}

Recommendations:
{recommendations_text if recommendations_text else "- No specific recommendations"}

Please fix the code to address these structural issues while maintaining the original design intent.
Ensure all bricks are:
1. On 8mm X/Y grid
2. At correct Z-axis heights (9.6mm per layer)
3. Using only standard brick sizes (2x2, 2x4, 2x6, 1x2, 1x4, 1x6)
4. Connected to structure below OR above
5. Staggered to avoid long vertical seams
"""

    def get_last_buildability_result(self) -> Optional[BuildabilityResult]:
        """Get the most recent buildability validation result.

        Returns:
            The last BuildabilityResult, or None if no validation has been run.
        """
        return self._last_buildability_result

    def _extract_or_generate_stl(self, coder_output: str) -> tuple[str | None, str | None]:
        """Extracts STL path from output or attempts fallback generation.

        Args:
            coder_output (str): The full text output from the Coder Agent.

        Returns:
            tuple[str | None, str | None]: A tuple containing (stl_path, error_message).
                If successful, stl_path is str and error_message is None.
                If failed, stl_path is None and error_message is str.
        """
        # Extract STL path
        stl_match = re.search(r"outputs/[\w-]+\.stl", coder_output)

        if stl_match:
            return stl_match.group(0), None

        logger.info("ControlFlow: No STL file found in output. Checking for code block...")
        # Fallback: Check if code was outputted in markdown
        code_match = re.search(r"```python(.*?)```", coder_output, re.DOTALL)
        if code_match:
            logger.info("ControlFlow: Found code block. Executing fallback generation...")
            code = code_match.group(1).strip()
            result = create_cad_model(code)
            if result["success"]:
                logger.info(f"ControlFlow: Fallback generation successful. Files: {result['files']}")
                return result['files']['stl'], None
            else:
                logger.error(f"ControlFlow: Fallback generation failed: {result['error']}")
                return None, result['error']

        return None, "No code block or STL file found."

    async def _get_designer_feedback(self, png_path: str, original_spec: str, user_id: str, session_id: str) -> str:
        """Requests feedback from the Designer Verification Agent on the rendered image.

        Uses the Flash model for faster verification feedback loops.

        Args:
            png_path (str): Path to the rendered PNG image.
            original_spec (str): The original design specification.
            user_id (str): The unique identifier for the user.
            session_id (str): The unique identifier for the session.

        Returns:
            str: The feedback text from the Designer Verification Agent.
        """
        logger.info("--- Requesting Designer Verification (Flash) ---")
        # Use the lightweight verification agent (Flash model) for speed
        designer_runner = Runner(
            agent=self.designer_verification_agent,
            app_name=self.app_name,
            session_service=self.session_service,
            memory_service=self.memory_service
        )
        
        with open(png_path, "rb") as f:
            image_data = f.read()
            
        feedback_prompt = f"""Original Specification:
{original_spec[:1000]}...

Compare this rendered image against the specification above."""
        
        feedback_input = Content(parts=[
            Part(text=feedback_prompt),
            Part(inline_data={"mime_type": "image/png", "data": image_data})
        ], role="user")
        
        feedback_output = ""
        async for event in designer_runner.run_async(user_id=user_id, session_id=session_id, new_message=feedback_input):
            if event.is_final_response() and event.content and event.content.parts:
                feedback_output = event.content.parts[0].text
                logger.info(f"ControlFlow: Designer Verification Feedback:\n{feedback_output}")
        
        return feedback_output


    async def _verify_model(
        self,
        stl_path: str,
        original_spec: str,
        user_id: str,
        session_id: str,
        skip_verification: bool = False
    ) -> tuple[bool, str, str | None]:
        """Renders the model and optionally gets feedback from the Designer.

        Args:
            stl_path: Path to the STL file.
            original_spec: The original specification.
            user_id: User ID.
            session_id: Session ID.
            skip_verification: If True, skip Designer feedback (for high buildability scores).

        Returns:
            tuple: (is_approved, feedback_text, png_path)
        """
        logger.info(f"ControlFlow: Found STL at {stl_path}")
        
        # Use async rendering for better performance
        png_path = await render_stl_async(stl_path)
        if not png_path:
            logger.error("ControlFlow: Failed to render STL.")
            return False, "Failed to render STL.", None
            
        logger.info(f"ControlFlow: Rendered image at {png_path}")
        
        # Skip Designer verification if buildability score is high
        if skip_verification:
            logger.info("ControlFlow: Skipping Designer verification (high buildability score)")
            return True, "APPROVED: Model passed buildability validation with high score.", png_path
        
        # Ask Designer for Feedback (using Flash model)
        feedback_output = await self._get_designer_feedback(png_path, original_spec, user_id, session_id)
        
        is_approved = "APPROVED" in feedback_output
        return is_approved, feedback_output, png_path

    async def _execute_loop_iteration(
        self,
        current_spec: str,
        original_spec: str,
        user_id: str,
        session_id: str,
        skip_buildability_correction: bool = False
    ) -> AsyncGenerator[str | tuple[bool, str], None]:
        """Executes one iteration of the feedback loop.

        Args:
            current_spec (str): The current specification to code.
            original_spec (str): The original specification for reference.
            user_id (str): The unique identifier for the user.
            session_id (str): The unique identifier for the session.
            skip_buildability_correction (bool): If True, skip auto-correction for buildability.

        Yields:
            Union[str, tuple[bool, str]]: Chunks of text output, and finally a tuple (is_approved, next_spec).
        """
        # 1. Generate Model
        # Note: We can't easily stream the coder output here if we refactor to _generate_model
        # unless we pass the yield callback or keep the generator logic inline.
        # To preserve streaming, we'll keep the generator call here but use the helper logic for the rest.

        coder_result = {}
        async for chunk in self._run_coder_step(current_spec, user_id, session_id, coder_result):
            yield chunk

        coder_output = coder_result.get("output", "")
        stl_path, generation_error = self._extract_or_generate_stl(coder_output)

        if not stl_path:
            logger.error(f"ControlFlow: Generation failed. Error: {generation_error}")
            logger.info("ControlFlow: Sending error back to Coder...")
            next_spec = f"Original Specification:\n{original_spec}\n\nPrevious attempt failed with error:\n{generation_error}\n\nPlease fix the code."
            yield (False, next_spec)
            return

        # 2. Validate Buildability (if metadata available)
        model_metadata = self._extract_model_metadata(coder_output)
        skip_designer_verification = False  # Track if we should skip verification
        
        if model_metadata.get("build_sequence") and not skip_buildability_correction:
            validation_result, needs_correction = self._validate_and_maybe_correct(
                model_metadata, coder_output, original_spec
            )

            if needs_correction:
                logger.info(f"ControlFlow: Buildability score {validation_result.score} < {BUILDABILITY_THRESHOLD}, "
                           f"attempting self-correction")
                yield f"Buildability check: score {validation_result.score}/100 - attempting correction...\n"

                # Build correction prompt and retry (does NOT count against user retry limit)
                correction_spec = self._build_correction_prompt(original_spec, validation_result)

                # Run coder again with correction prompt
                correction_result = {}
                async for chunk in self._run_coder_step(correction_spec, user_id, session_id, correction_result):
                    pass  # Don't yield correction output to avoid confusion

                corrected_output = correction_result.get("output", "")
                corrected_stl, corrected_error = self._extract_or_generate_stl(corrected_output)

                if corrected_stl:
                    stl_path = corrected_stl
                    coder_output = corrected_output

                    # Re-validate corrected model
                    corrected_metadata = self._extract_model_metadata(corrected_output)
                    if corrected_metadata.get("build_sequence"):
                        corrected_validation = validate_buildability(corrected_metadata)
                        self._last_buildability_result = corrected_validation
                        logger.info(f"ControlFlow: Corrected buildability score: {corrected_validation.score}")
                        yield f"Corrected buildability score: {corrected_validation.score}/100\n"
                        
                        # Check if corrected score is high enough to skip verification
                        if corrected_validation.score >= HIGH_BUILDABILITY_SKIP_THRESHOLD:
                            skip_designer_verification = True
                            logger.info(f"ControlFlow: High buildability score {corrected_validation.score} >= {HIGH_BUILDABILITY_SKIP_THRESHOLD}, will skip Designer verification")
                else:
                    logger.warning(f"ControlFlow: Self-correction failed, using original model")
                    yield "Self-correction failed, using original model.\n"
            else:
                # Buildability validation passed - check if score is high enough to skip verification
                if validation_result.score >= HIGH_BUILDABILITY_SKIP_THRESHOLD:
                    skip_designer_verification = True
                    logger.info(f"ControlFlow: High buildability score {validation_result.score} >= {HIGH_BUILDABILITY_SKIP_THRESHOLD}, will skip Designer verification")
        else:
            # No build_sequence metadata from coder - use STL rendering instead
            # Synthetic colored brick rendering is disabled until Coder reliably outputs build_sequence
            logger.info("ControlFlow: No build_sequence from coder, using STL rendering")
            self._last_buildability_result = None

        # 3. Verify Model with Designer (may be skipped for high buildability scores)
        is_approved, feedback_output, png_path = await self._verify_model(
            stl_path, original_spec, user_id, session_id, 
            skip_verification=skip_designer_verification
        )

        if png_path:
            yield f"Generated Image: {png_path}\n"
        else:
            yield "\nFailed to render STL.\n"
            yield (False, current_spec)
            return

        if is_approved:
            logger.info("ControlFlow: Design Approved.")
            friendly_msg = feedback_output.replace("APPROVED", "").strip()
            if not friendly_msg:
                    friendly_msg = "Here is your 3D model."
            yield f"{friendly_msg}\n"
            yield (True, "")
        else:
            logger.info("ControlFlow: Design Rejected. Retrying...")
            yield f"Designer Feedback: {feedback_output}\n"
            next_spec = f"Original Specification:\n{original_spec}\n\nFeedback on previous attempt:\n{feedback_output}\n\nPlease fix the code based on this feedback."
            yield (False, next_spec)

    async def run(
        self, 
        prompt: str, 
        session_id: str, 
        user_id: str = "user",
        generation_options: GenerateOptions | None = None
    ) -> AsyncGenerator[str, None]:
        """Executes the agent workflow: Designer -> Coder -> Renderer -> Designer (Feedback) -> Coder (Fix).

        Args:
            prompt (str): The user's request.
            session_id (str): The unique identifier for the session.
            user_id (str): The unique identifier for the user.
            generation_options (GenerateOptions | None): Optional generation options.

        Yields:
            str: Chunks of text output describing the process and results.
        """
        await self._ensure_session(session_id, user_id)

        # Inject complexity/size context into the prompt
        context_header = ""
        if generation_options:
            complexity = generation_options.complexity or "normal"
            model_size = generation_options.model_size or "small"
            context_header = f"""[GENERATION CONTEXT]
Complexity: {complexity.upper()}
Model Size: {str(model_size).upper() if model_size else 'STANDARD'}
IMPORTANT: Even in NORMAL/ADVANCED mode, the output MUST be a LEGO brick-based model with voxel aesthetic.
Advanced mode means MORE LEGO detail and precision, NOT smooth CAD surfaces.
---

"""
        enhanced_prompt = context_header + prompt

        # Run Designer Agent first to build the initial task / specification. 
        designer_output = await self._run_designer_step(enhanced_prompt, user_id, session_id)
        yield f"Design Specification:\n{designer_output[:100]}...\n"

        # After design specification is generated, run the loops of coder -> renderer -> designer -> coder until approved or max loops reached.
        max_loops = 3
        current_spec = designer_output
        
        for loop in range(max_loops):
            logger.info(f"--- Running Coder Agent (Loop {loop+1}) ---")
            
            async for chunk in self._execute_loop_iteration(current_spec, designer_output, user_id, session_id):
                if isinstance(chunk, tuple):
                    # Final result of the iteration
                    is_approved, next_spec = chunk
                    if is_approved:
                        return
                    current_spec = next_spec
                else:
                    # Streaming output
                    yield chunk
        
        # If loop finishes without approval
        yield "I'm sorry, I was unable to generate the model correctly after multiple attempts.\n"

    async def _run_modifier_step(
        self,
        existing_code: str,
        modification_prompt: str,
        user_id: str,
        session_id: str,
        result_container: dict[str, str]
    ) -> AsyncGenerator[str, None]:
        """Runs the Modifier Agent to modify existing code.

        Args:
            existing_code (str): The existing build123d code to modify.
            modification_prompt (str): The user's modification request.
            user_id (str): The unique identifier for the user.
            session_id (str): The unique identifier for the session.
            result_container (dict[str, str]): A dictionary to store the full output string.

        Yields:
            str: Chunks of the generated text output.
        """
        logger.info("--- Running Modifier Agent ---")

        # Create the modifier agent with RAG context
        modifier_agent = self.code_modifier.create_modifier_agent(
            existing_code=existing_code,
            modification_prompt=modification_prompt
        )

        modifier_runner = Runner(
            agent=modifier_agent,
            app_name=self.app_name,
            session_service=self.session_service,
            memory_service=self.memory_service
        )

        # The modifier agent just needs to know to apply the modification
        # The instruction is already baked into the agent's system prompt
        modifier_input = Content(
            parts=[Part(text=f"Apply the modification: {modification_prompt}")],
            role="user"
        )

        modifier_output = ""

        async for event in modifier_runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=modifier_input
        ):
            if event.content:
                tool_output = self._parse_tool_output(event.content)
                if tool_output:
                    modifier_output += f"\nTool Output: {tool_output}"

            if event.is_final_response() and event.content and event.content.parts:
                text_parts = [p.text for p in event.content.parts if p.text]
                if text_parts:
                    chunk = "\n" + "\n".join(text_parts)
                    modifier_output += chunk
                    yield "\n".join(text_parts)

        result_container["output"] = modifier_output
        logger.info(f"ControlFlow: Modifier Output Raw: {modifier_output}")

    async def _execute_modification_iteration(
        self,
        existing_code: str,
        modification_prompt: str,
        user_id: str,
        session_id: str
    ) -> AsyncGenerator[str | tuple[bool, str], None]:
        """Executes one iteration of the modification workflow.

        Args:
            existing_code (str): The existing build123d code.
            modification_prompt (str): The user's modification request.
            user_id (str): The unique identifier for the user.
            session_id (str): The unique identifier for the session.

        Yields:
            Union[str, tuple[bool, str]]: Chunks of text output, and finally a tuple (success, message).
        """
        # 1. Run Modifier
        modifier_result = {}
        async for chunk in self._run_modifier_step(
            existing_code, modification_prompt, user_id, session_id, modifier_result
        ):
            yield chunk

        modifier_output = modifier_result.get("output", "")
        stl_path, generation_error = self._extract_or_generate_stl(modifier_output)

        if not stl_path:
            logger.error(f"ControlFlow: Modification failed. Error: {generation_error}")
            yield (False, f"Modification failed: {generation_error}")
            return

        # 2. Validate Buildability (if metadata available) - same as generation workflow
        model_metadata = self._extract_model_metadata(modifier_output)
        skip_designer_verification = False

        if model_metadata.get("build_sequence"):
            validation_result = validate_buildability(model_metadata)
            self._last_buildability_result = validation_result
            logger.info(f"ControlFlow: Modification buildability score: {validation_result.score}")
            
            # Check if score is high enough to skip Designer verification
            if validation_result.score >= HIGH_BUILDABILITY_SKIP_THRESHOLD:
                skip_designer_verification = True
                logger.info(f"ControlFlow: High buildability score {validation_result.score} >= "
                           f"{HIGH_BUILDABILITY_SKIP_THRESHOLD}, skipping Designer verification")
        else:
            logger.info("ControlFlow: No build_sequence from modifier, using STL rendering only")
            self._last_buildability_result = None

        # 3. Verify Modified Model (may be skipped for high buildability)
        is_approved, feedback_output, png_path = await self._verify_model(
            stl_path, f"Modified version of existing model: {modification_prompt}",
            user_id, session_id,
            skip_verification=skip_designer_verification
        )

        if png_path:
            yield f"Modified Model Image: {png_path}\n"
        else:
            yield "\nFailed to render modified STL.\n"
            yield (False, "Render failed")
            return

        if is_approved:
            logger.info("ControlFlow: Modified Design Approved.")
            friendly_msg = feedback_output.replace("APPROVED", "").strip()
            if not friendly_msg:
                friendly_msg = "Here is your modified 3D model."
            yield f"{friendly_msg}\n"
            yield (True, "")
        else:
            logger.info("ControlFlow: Modified Design Needs Adjustment.")
            yield f"Designer Feedback: {feedback_output}\n"
            yield (False, feedback_output)

    async def run_modification(
        self,
        existing_code: str,
        modification_prompt: str,
        session_id: str,
        user_id: str = "user",
        inventory: list | None = None
    ) -> AsyncGenerator[str, None]:
        """Executes the modification workflow: Modifier -> Renderer -> Designer (Feedback).

        Unlike generation, modification skips the initial Designer step and goes
        directly to code modification using the existing code as base.

        Args:
            existing_code (str): The existing build123d code to modify.
            modification_prompt (str): The user's modification request (e.g., "make it taller").
            session_id (str): The unique identifier for the session.
            user_id (str): The unique identifier for the user.
            inventory (list | None): Optional list of available bricks for validation.

        Yields:
            str: Chunks of text output describing the process and results.
        """
        await self._ensure_session(session_id, user_id)

        logger.info(f"ControlFlow: Starting modification workflow for: {modification_prompt[:100]}...")
        yield f"Modifying model: {modification_prompt}\n"

        # Validate existing code before attempting modification (including inventory check)
        is_valid, errors = self.code_modifier.validate_modified_code(existing_code, inventory)
        if not is_valid:
            error_msg = f"Invalid base code. Errors: {', '.join(errors)}"
            logger.error(f"ControlFlow: {error_msg}")
            yield f"Error: {error_msg}\n"
            yield "Modification not possible. Try rephrasing or use regenerate.\n"
            return

        # Run modification loop (fewer iterations than generation since we have a base)
        max_loops = 2
        current_code = existing_code

        for loop in range(max_loops):
            logger.info(f"--- Running Modification Loop {loop+1} ---")

            async for chunk in self._execute_modification_iteration(
                current_code, modification_prompt, user_id, session_id
            ):
                if isinstance(chunk, tuple):
                    # Final result of the iteration
                    success, message = chunk
                    if success:
                        return
                    # If not successful and we have more loops, continue
                    if loop < max_loops - 1:
                        yield f"Retrying modification with feedback: {message[:100]}...\n"
                else:
                    # Streaming output
                    yield chunk

        # If loop finishes without success
        yield "Modification not possible. Try rephrasing or use regenerate.\n"
