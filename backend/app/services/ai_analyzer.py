"""
AI-powered log analysis service supporting multiple AI providers
"""
import logging
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers"""
    CLAUDE = "claude"
    OPENAI = "openai"
    OLLAMA = "ollama"


class LogType(str, Enum):
    """Supported log types"""
    FGT = "fgt"  # FortiGate logs
    FAC = "fac"  # FortiAuthenticator logs
    PYTEST = "pytest"  # Pytest automation logs
    GENERIC = "generic"  # Generic application logs


class AILogAnalyzer:
    """AI-powered log analyzer supporting multiple providers"""

    def __init__(
        self,
        provider: AIProvider = AIProvider.CLAUDE,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        ollama_url: str = "http://localhost:11434"
    ):
        """
        Initialize AI log analyzer

        Args:
            provider: AI provider to use
            api_key: API key for Claude/OpenAI
            model: Model to use (optional, uses defaults)
            ollama_url: Ollama server URL
        """
        self.provider = provider
        self.api_key = api_key
        self.ollama_url = ollama_url

        # Default models
        if model:
            self.model = model
        else:
            if provider == AIProvider.CLAUDE:
                self.model = "claude-3-5-sonnet-20241022"
            elif provider == AIProvider.OPENAI:
                self.model = "gpt-4o"
            elif provider == AIProvider.OLLAMA:
                self.model = "llama3.1"

        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate AI client"""
        if self.provider == AIProvider.CLAUDE:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        elif self.provider == AIProvider.OPENAI:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        elif self.provider == AIProvider.OLLAMA:
            import requests
            self.client = requests  # Use requests for Ollama HTTP API

    def analyze_logs(
        self,
        logs: str,
        log_type: LogType = LogType.GENERIC,
        test_name: Optional[str] = None,
        focus_areas: Optional[List[str]] = None
    ) -> Dict:
        """
        Analyze logs using AI

        Args:
            logs: Log content to analyze
            log_type: Type of logs (FGT, FAC, PYTEST, GENERIC)
            test_name: Optional test name
            focus_areas: Optional list of specific areas to focus on

        Returns:
            Analysis results dictionary
        """
        # Build prompt based on log type
        prompt = self._build_analysis_prompt(logs, log_type, test_name, focus_areas)

        # Get AI response
        try:
            if self.provider == AIProvider.CLAUDE:
                response = self._analyze_with_claude(prompt)
            elif self.provider == AIProvider.OPENAI:
                response = self._analyze_with_openai(prompt)
            elif self.provider == AIProvider.OLLAMA:
                response = self._analyze_with_ollama(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            # Parse and structure the response
            analysis = self._parse_analysis_response(response, log_type)

            return {
                "success": True,
                "provider": self.provider.value,
                "model": self.model,
                "log_type": log_type.value,
                "analysis": analysis
            }
        except Exception as e:
            logger.error(f"AI log analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider.value
            }

    def _build_analysis_prompt(
        self,
        logs: str,
        log_type: LogType,
        test_name: Optional[str],
        focus_areas: Optional[List[str]]
    ) -> str:
        """Build analysis prompt based on log type"""

        base_context = {
            LogType.FGT: "FortiGate mobile application logs",
            LogType.FAC: "FortiAuthenticator mobile application logs",
            LogType.PYTEST: "Pytest automation test logs",
            LogType.GENERIC: "Application logs"
        }

        context = base_context.get(log_type, "Application logs")

        prompt = f"""You are an expert QA engineer analyzing {context}.

"""

        if test_name:
            prompt += f"Test Name: {test_name}\n\n"

        if focus_areas:
            prompt += f"Focus Areas: {', '.join(focus_areas)}\n\n"

        prompt += f"""Analyze the following logs and provide:

1. **Summary**: Brief overview of what happened
2. **Error Analysis**: Identify all errors, warnings, and failures
3. **Root Cause**: Determine the most likely root cause(s)
4. **Severity**: Rate severity (Critical, High, Medium, Low)
5. **Recommendations**: Specific actionable steps to fix the issues
6. **Test Impact**: How this affects test reliability and pass rate

Logs:
```
{logs[:10000]}  # Limit to first 10k chars for token efficiency
```

Provide your analysis in a structured format."""

        return prompt

    def _analyze_with_claude(self, prompt: str) -> str:
        """Analyze using Claude API"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text

    def _analyze_with_openai(self, prompt: str) -> str:
        """Analyze using OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert QA engineer analyzing test logs."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000
        )
        return response.choices[0].message.content

    def _analyze_with_ollama(self, prompt: str) -> str:
        """Analyze using Ollama API"""
        response = self.client.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()["response"]

    def _parse_analysis_response(self, response: str, log_type: LogType) -> Dict:
        """Parse and structure the AI analysis response"""

        # Try to extract structured sections
        sections = {
            "summary": "",
            "errors": [],
            "root_cause": "",
            "severity": "Unknown",
            "recommendations": [],
            "test_impact": "",
            "raw_response": response
        }

        # Simple regex-based parsing
        summary_match = re.search(r'\*\*Summary\*\*[:\s]*(.*?)(?=\*\*|$)', response, re.DOTALL | re.IGNORECASE)
        if summary_match:
            sections["summary"] = summary_match.group(1).strip()

        root_cause_match = re.search(r'\*\*Root Cause\*\*[:\s]*(.*?)(?=\*\*|$)', response, re.DOTALL | re.IGNORECASE)
        if root_cause_match:
            sections["root_cause"] = root_cause_match.group(1).strip()

        severity_match = re.search(r'\*\*Severity\*\*[:\s]*(Critical|High|Medium|Low)', response, re.IGNORECASE)
        if severity_match:
            sections["severity"] = severity_match.group(1).capitalize()

        impact_match = re.search(r'\*\*Test Impact\*\*[:\s]*(.*?)(?=\*\*|$)', response, re.DOTALL | re.IGNORECASE)
        if impact_match:
            sections["test_impact"] = impact_match.group(1).strip()

        # Extract errors and recommendations (list items)
        error_section = re.search(r'\*\*Error Analysis\*\*[:\s]*(.*?)(?=\*\*|$)', response, re.DOTALL | re.IGNORECASE)
        if error_section:
            errors_text = error_section.group(1)
            sections["errors"] = [
                line.strip('- •*').strip()
                for line in errors_text.split('\n')
                if line.strip() and (line.strip().startswith('-') or line.strip().startswith('•') or line.strip().startswith('*'))
            ]

        rec_section = re.search(r'\*\*Recommendations\*\*[:\s]*(.*?)(?=\*\*|$)', response, re.DOTALL | re.IGNORECASE)
        if rec_section:
            rec_text = rec_section.group(1)
            sections["recommendations"] = [
                line.strip('- •*').strip()
                for line in rec_text.split('\n')
                if line.strip() and (line.strip().startswith('-') or line.strip().startswith('•') or line.strip().startswith('*'))
            ]

        return sections

    def suggest_fixes(self, error_message: str, context: Optional[Dict] = None) -> List[str]:
        """
        Get fix suggestions for a specific error

        Args:
            error_message: The error message
            context: Optional context (test name, environment, etc.)

        Returns:
            List of suggested fixes
        """
        context_str = ""
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])

        prompt = f"""Given the following error, provide 3-5 specific, actionable fix suggestions:

Error: {error_message}

{context_str if context_str else ''}

Provide numbered suggestions that a QA engineer can implement immediately."""

        try:
            if self.provider == AIProvider.CLAUDE:
                response = self._analyze_with_claude(prompt)
            elif self.provider == AIProvider.OPENAI:
                response = self._analyze_with_openai(prompt)
            elif self.provider == AIProvider.OLLAMA:
                response = self._analyze_with_ollama(prompt)

            # Extract numbered suggestions
            suggestions = []
            for line in response.split('\n'):
                if re.match(r'^\d+\.', line.strip()):
                    suggestions.append(line.strip())

            return suggestions if suggestions else [response]
        except Exception as e:
            logger.error(f"Failed to get fix suggestions: {e}")
            return [f"Error getting suggestions: {str(e)}"]

    def compare_test_runs(
        self,
        previous_log: str,
        current_log: str,
        test_name: str
    ) -> Dict:
        """
        Compare two test runs and identify regressions or improvements

        Args:
            previous_log: Previous test run log
            current_log: Current test run log
            test_name: Test name

        Returns:
            Comparison analysis
        """
        prompt = f"""Compare these two test run logs for '{test_name}' and identify:

1. New issues introduced
2. Fixed issues
3. Performance changes
4. Stability changes

Previous Run:
```
{previous_log[:5000]}
```

Current Run:
```
{current_log[:5000]}
```

Provide a structured comparison."""

        try:
            if self.provider == AIProvider.CLAUDE:
                response = self._analyze_with_claude(prompt)
            elif self.provider == AIProvider.OPENAI:
                response = self._analyze_with_openai(prompt)
            elif self.provider == AIProvider.OLLAMA:
                response = self._analyze_with_ollama(prompt)

            return {
                "success": True,
                "test_name": test_name,
                "comparison": response
            }
        except Exception as e:
            logger.error(f"Failed to compare test runs: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Factory function to create analyzer with default configuration
def create_analyzer(
    provider: str = "claude",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> AILogAnalyzer:
    """
    Create AI log analyzer with default configuration

    Args:
        provider: AI provider name (claude, openai, ollama)
        api_key: API key (optional, uses environment variables)
        model: Model name (optional, uses defaults)

    Returns:
        AILogAnalyzer instance
    """
    import os

    # Get API keys from environment if not provided
    if not api_key:
        if provider == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")

    provider_enum = AIProvider(provider.lower())

    return AILogAnalyzer(
        provider=provider_enum,
        api_key=api_key,
        model=model
    )
