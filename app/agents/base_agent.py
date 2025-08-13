import json
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from modules.users.models import User
from agents.prompts.system_prompts import SYSTEM_PROMPTS
from app.communication.llm import (
    llm_service,
    LLMServiceError,
    LLMTimeoutError,
    LLMAPIError,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base agent class for all AI agents in the system.
    Stateless processing - each message is independent.
    """

    def __init__(self, agent_name: str, user: User):
        self.agent_name = agent_name
        self.user = user

    def build_prompt(self, message: str) -> str:
        """
        Build a comprehensive prompt including system instructions and user context.
        No conversation history for stateless processing.
        """
        # Get the base system prompt
        system_prompt = SYSTEM_PROMPTS.get(
            self.agent_name, SYSTEM_PROMPTS["base_agent"]
        )

        # Format with current date
        system_prompt = system_prompt.format(
            current_date=datetime.now().strftime("%Y-%m-%d")
        )

        # Add user context
        user_context = f"""
User Information:
- User ID: {self.user.id}
- Phone: {self.user.phone_number}
- Streak: {self.user.streak} days
- Metadata: {json.dumps(self.user.meta) if self.user.meta else 'None'}
- Currency: INR (₹)
"""

        # Combine all parts
        full_prompt = (
            f"{system_prompt}\n{user_context}\nUser Message: {message}\n\nAssistant:"
        )

        return full_prompt

    async def call_llm(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7
    ) -> str:
        """
        Make an async call to the LLM using the centralized LLM service.
        """
        try:
            response = await llm_service.complete(
                prompt=prompt, max_tokens=max_tokens, temperature=temperature
            )
            return response.content
        except (LLMServiceError, LLMTimeoutError, LLMAPIError) as e:
            logger.error(f"LLM service error: {str(e)}")
            return "I encountered an issue and couldn't complete the request. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error during LLM call: {str(e)}")
            return "I encountered an issue and couldn't complete the request. Please try again later."

    def parse_response(self, llm_response: str) -> Dict[str, Any]:
        """
        Parse the LLM response to extract structured data.
        Enhanced with validation for better reliability.
        """
        try:
            # Try to find JSON in the response
            start_idx = llm_response.find("{")
            end_idx = llm_response.rfind("}")

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = llm_response[start_idx : end_idx + 1]
                parsed_json = json.loads(json_str)

                # Validate parsed JSON
                if self.validate_parsed_response(parsed_json):
                    return {
                        "type": "structured",
                        "data": parsed_json,
                        "raw_response": llm_response,
                    }
                else:
                    logger.warning(f"Invalid JSON structure from LLM: {parsed_json}")

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")

        # If no valid JSON found, return as plain text
        return {
            "type": "text",
            "data": {"message": llm_response.strip()},
            "raw_response": llm_response,
        }

    def validate_parsed_response(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Validate that parsed response has required structure.
        Can be overridden by specialized agents for specific validation.
        """
        # Base validation - check for action field
        if not isinstance(parsed_data, dict):
            return False

        # Most agents should return an action
        return "action" in parsed_data

    @abstractmethod
    def execute_action(self, parsed_response: Dict[str, Any]) -> str:
        """
        Execute actions based on the parsed response.
        This method must be implemented by subclasses.
        """
        pass

    async def process_message(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Main entry point for processing user messages.
        Stateless processing - each call is independent.
        """
        try:
            logger.info(
                f"Agent {self.agent_name} processing message for user {self.user.id}"
            )

            # Validate input
            if not message or not message.strip():
                return "I didn't receive any message. Could you please try again?"

            # Build the prompt (with optional context from message handler)
            prompt = self.build_prompt_with_context(message, context)

            # Call the LLM
            llm_response = await self.call_llm(prompt)

            # Parse the response
            parsed_response = self.parse_response(llm_response)

            # Execute any actions
            action_result = self.execute_action(parsed_response)

            # Post-process the response
            final_response = self.post_process_response(action_result or llm_response)

            logger.info(f"Agent {self.agent_name} completed processing")
            return final_response

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return "I apologize, but I encountered an error while processing your message. Please try again."

    def build_prompt_with_context(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build prompt with optional context from message handler (intent, entities, etc.).
        """
        base_prompt = self.build_prompt(message)

        if context:
            context_info = []
            if "intent" in context:
                context_info.append(f"Detected Intent: {context['intent']}")
            if "entities" in context:
                entities_str = json.dumps(context["entities"])
                context_info.append(f"Extracted Entities: {entities_str}")
            if "confidence" in context:
                context_info.append(f"Confidence: {context['confidence']}")

            if context_info:
                context_section = (
                    "\nAdditional Context:\n" + "\n".join(context_info) + "\n"
                )
                # Insert context before the user message
                base_prompt = base_prompt.replace(
                    "User Message:", f"{context_section}User Message:"
                )

        return base_prompt

    def post_process_response(self, response: str) -> str:
        """
        Post-process the response before sending to user.
        Add currency formatting, length limits, streak motivation, etc.
        """
        if not response:
            return "I apologize, but I couldn't generate a proper response."

        # Ensure INR currency formatting
        import re

        # Add ₹ symbol if numbers are mentioned without currency
        response = re.sub(r"\b(\d+(?:\.\d{2})?)\b(?!\s*₹)", r"₹\1", response)

        # Ensure response is not too long for WhatsApp
        if len(response) > 4000:
            response = response[:3950] + "... (message truncated)"

        # Add streak motivation for positive interactions
        if any(
            word in response.lower()
            for word in ["added", "created", "updated", "saved", "success"]
        ):
            if self.user.streak > 0:
                response += (
                    f"\n\n🔥 You're on a {self.user.streak}-day streak! Keep it up!"
                )

        return response

    def get_user_context(self) -> Dict[str, Any]:
        """
        Get user context as dictionary for use in business logic.
        """
        return {
            "user_id": str(self.user.id),
            "phone_number": self.user.phone_number,
            "streak": self.user.streak,
            "meta": self.user.meta or {},
        }

    def __str__(self) -> str:
        return f"{self.agent_name} for user {self.user.id}"


class FinanceAgent(BaseAgent):
    """
    Main finance agent that acts as coordinator and fallback.
    Routes to specialized agents when needed.
    """

    def __init__(self, user: User):
        super().__init__("finance_agent", user)

    def validate_parsed_response(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Finance agent accepts various action types.
        """
        if not isinstance(parsed_data, dict):
            return False

        # Finance agent can handle various actions or just return messages
        return True  # More flexible validation for main coordinator

    def execute_action(self, parsed_response: Dict[str, Any]) -> str:
        """
        Execute actions for finance agent or delegate to specialized agents.
        """
        if parsed_response["type"] == "structured":
            data = parsed_response["data"]
            action = data.get("action")

            # Route to specialized agents based on action
            if action and action.startswith("expense_"):
                return self.route_to_expense_agent(
                    data, parsed_response["raw_response"]
                )
            elif action and action.startswith("budget_"):
                return "Yet to implement budget routing"  # Placeholder for budget agent
                # return self.route_to_budget_agent(data, parsed_response["raw_response"])
            elif action and action.startswith("report_"):
                return "Yet to implement report routing"  # Placeholder for report agent
                # return self.route_to_report_agent(data, parsed_response["raw_response"])
            else:
                # Handle generic finance queries
                return self.handle_generic_finance_action(data)

        # Return the LLM response for text-type responses
        return parsed_response["data"]["message"]

    def route_to_expense_agent(self, data: Dict[str, Any], raw_response: str) -> str:
        """Route to expense agent (lazy loaded)."""
        try:

            from app.agents.expense_agent import ExpenseTrackerAgent

            expense_agent = ExpenseTrackerAgent(self.user)
            return expense_agent.execute_action(
                {"type": "structured", "data": data, "raw_response": raw_response}
            )
        except Exception as e:
            logger.error(f"Error routing to expense agent: {e}")
            return "I had trouble processing your expense request. Please try again."

    # def route_to_budget_agent(self, data: Dict[str, Any], raw_response: str) -> str:
    #     """Route to budget agent (lazy loaded)."""
    #     try:
    #         from agents.budget_advisor_agent import BudgetAdvisorAgent

    #         budget_agent = BudgetAdvisorAgent(self.user)
    #         return budget_agent.execute_action(
    #             {"type": "structured", "data": data, "raw_response": raw_response}
    #         )
    #     except Exception as e:
    #         logger.error(f"Error routing to budget agent: {e}")
    #         return "I had trouble processing your budget request. Please try again."

    # def route_to_report_agent(self, data: Dict[str, Any], raw_response: str) -> str:
    #     """Route to report agent (lazy loaded)."""
    #     try:
    #         from agents.report_generator_agent import ReportGeneratorAgent

    #         report_agent = ReportGeneratorAgent(self.user)
    #         return report_agent.execute_action(
    #             {"type": "structured", "data": data, "raw_response": raw_response}
    #         )
    #     except Exception as e:
    #         logger.error(f"Error routing to report agent: {e}")
    #         return "I had trouble generating your report. Please try again."

    def handle_generic_finance_action(self, data: Dict[str, Any]) -> str:
        """Handle generic finance queries that don't need specialized agents."""
        action = data.get("action", "")

        if action == "help":
            return self.get_help_message()
        elif action == "greeting":
            return f"Hello! I'm your personal finance assistant. I can help you track expenses, manage budgets, and generate reports. What would you like to do today?"
        else:
            return data.get(
                "message", "I'm here to help with your personal finance needs!"
            )

    def get_help_message(self) -> str:
        """Return help message with available commands."""
        return """I can help you with:

💰 **Expenses**: Add, track, and manage your expenses
Example: "Add ₹500 for groceries at BigBasket"

📊 **Budgets**: Set and monitor your spending budgets  
Example: "Set my grocery budget to ₹3000 per month"

📈 **Reports**: Generate spending reports and insights
Example: "Show me this month's expenses"

🎯 **Goals**: Set and track financial goals
Example: "I want to save ₹50000 for vacation"

Just tell me what you'd like to do in natural language!"""
