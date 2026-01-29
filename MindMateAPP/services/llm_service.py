"""
LLM Service - Universal wrapper for AI model interactions
Supports: Llama3 (via Ollama), OpenAI, and other LLM providers
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"


class ModelType(Enum):
    """Common model types"""
    LLAMA3 = "llama3"
    LLAMA3_1 = "llama3.1"
    LLAMA3_2 = "llama3.2"
    GPT4 = "gpt-4"
    GPT35 = "gpt-3.5-turbo"


@dataclass
class LLMConfig:
    """Configuration for LLM service"""
    provider: ModelProvider = ModelProvider.OLLAMA
    model_name: str = "llama3"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30
    base_url: Optional[str] = None
    api_key: Optional[str] = None

    # Performance settings
    stream: bool = False
    top_p: float = 0.9
    top_k: int = 40

    # Macedonian language support - DEFAULT TO MACEDONIAN
    language: str = "mk"  # "mk" (Macedonian) or "en" (English)


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    finish_reason: str = "stop"
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LLMService:
    """
    Universal LLM service wrapper with fallback support

    Usage:
        service = LLMService()
        response = service.generate("What is machine learning?")
        print(response.content)
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM service with configuration"""
        self.config = config or LLMConfig()
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        try:
            if self.config.provider == ModelProvider.OLLAMA:
                self._initialize_ollama()
            elif self.config.provider == ModelProvider.OPENAI:
                self._initialize_openai()
            else:
                logger.warning(f"Unsupported provider: {self.config.provider}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")

    def _initialize_ollama(self):
        """Initialize Ollama client using HTTP requests (more reliable than Python client)"""
        try:
            # For Ollama, we'll use direct HTTP requests instead of the Python client
            # This is more reliable in Docker environments
            self.client = "ollama_http"  # Marker to use HTTP approach
            logger.info(f"✅ Ollama HTTP client configured for {self.config.base_url or 'localhost:11434'}")
        except Exception as e:
            logger.error(f"Failed to configure Ollama HTTP client: {e}")
            self.client = None

    def _initialize_openai(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")

            if not api_key:
                logger.warning("OpenAI API key not found")
                self.client = None
                return

            self.client = OpenAI(api_key=api_key)
            logger.info("✅ OpenAI client initialized successfully")
        except ImportError:
            logger.error("OpenAI package not installed. Install with: pip install openai")
            self.client = None

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Generate response from LLM

        Args:
            prompt: User prompt/query
            system_prompt: Optional system instructions
            temperature: Override default temperature
            max_tokens: Override default max tokens
            json_mode: Request JSON-formatted response

        Returns:
            LLMResponse object with generated content
        """
        if not self.client:
            return self._fallback_response(prompt)

        try:
            if self.config.provider == ModelProvider.OLLAMA:
                return self._generate_ollama(prompt, system_prompt, temperature, max_tokens, json_mode)
            elif self.config.provider == ModelProvider.OPENAI:
                return self._generate_openai(prompt, system_prompt, temperature, max_tokens, json_mode)
            else:
                return self._fallback_response(prompt)
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return self._fallback_response(prompt, error=str(e))

    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        json_mode: bool
    ) -> LLMResponse:
        """Generate response using Ollama via HTTP requests"""
        import requests
        
        # Build the full prompt
        full_prompt = ""
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\n"
        full_prompt += f"User: {prompt}"
        
        if json_mode:
            full_prompt += "\n\nRespond with valid JSON."
        
        ollama_url = self.config.base_url or "http://localhost:11434"
        
        payload = {
            "model": self.config.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": self.config.top_p,
                "top_k": self.config.top_k,
            }
        }
        
        try:
            response = requests.post(
                f"{ollama_url}/api/generate",
                json=payload,
                timeout=60  # Longer timeout for generation
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "").strip()
                
                return LLMResponse(
                    content=content,
                    model=self.config.model_name,
                    provider=self.config.provider.value,
                    finish_reason=result.get('done_reason', 'stop'),
                    metadata={
                        'eval_count': result.get('eval_count', 0),
                        'prompt_eval_count': result.get('prompt_eval_count', 0)
                    }
                )
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            logger.error(f"Ollama HTTP generation error: {e}")
            raise

    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        json_mode: bool
    ) -> LLMResponse:
        """Generate response using OpenAI"""
        messages = []

        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        kwargs = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)

            content = response.choices[0].message.content

            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.config.provider.value,
                tokens_used=response.usage.total_tokens,
                finish_reason=response.choices[0].finish_reason,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                }
            )
        except Exception as e:
            logger.error(f"OpenAI generation error: {e}")
            raise

    def _fallback_response(self, prompt: str, error: str = None) -> LLMResponse:
        """Provide fallback response when LLM is unavailable"""
        fallback_content = f"LLM service unavailable. Original query: {prompt[:100]}..."

        if error:
            fallback_content += f"\nError: {error}"

        return LLMResponse(
            content=fallback_content,
            model="fallback",
            provider="none",
            finish_reason="error",
            metadata={"error": error}
        )

    def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict],
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate response with function calling/tools support
        (For future LangGraph integration)
        """
        # This will be expanded for LangGraph tool integration
        return self.generate(prompt, system_prompt)

    def parse_json_response(self, response: LLMResponse) -> Optional[Dict]:
        """Parse JSON from LLM response"""
        try:
            # Try direct JSON parse
            return json.loads(response.content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_pattern = r'```json\s*(.*?)\s*```'
            match = re.search(json_pattern, response.content, re.DOTALL)

            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

            # Try to find any JSON object in the response
            json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            match = re.search(json_obj_pattern, response.content, re.DOTALL)

            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass

            logger.warning("Could not parse JSON from response")
            return None

    def is_available(self) -> bool:
        """Check if LLM service is available"""
        return self.client is not None

    def list_available_models(self) -> List[str]:
        """List available models"""
        if not self.client:
            return []

        try:
            if self.config.provider == ModelProvider.OLLAMA:
                # Use HTTP request for Ollama
                import requests
                ollama_url = self.config.base_url or "http://localhost:11434"
                response = requests.get(f"{ollama_url}/api/tags", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return [model['name'] for model in data.get('models', [])]
                return []
            elif self.config.provider == ModelProvider.OPENAI:
                # OpenAI models are known
                return ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")

        return []


# Singleton instance for easy access
_default_service = None


def get_llm_service(config: Optional[LLMConfig] = None) -> LLMService:
    """Get or create default LLM service instance"""
    global _default_service

    if _default_service is None or config is not None:
        _default_service = LLMService(config)

    return _default_service


# Convenience function
def quick_generate(prompt: str, system_prompt: str = None) -> str:
    """Quick generation without managing service instance"""
    service = get_llm_service()
    response = service.generate(prompt, system_prompt)
    return response.content


def classify_document_subject(content: str, max_length: int = 2000) -> str:
    """
    Classify the subject/topic of a document based on its content.
    Returns the identified subject in Macedonian.
    """
    import requests
    import re
    
    if not content or not content.strip():
        return "Општо"
    
    # Truncate content if too long
    content_sample = content[:max_length] if len(content) > max_length else content
    
    try:
        ollama_url = "http://host.docker.internal:11434"
        
        prompt = f"""Анализирај го внимателно следниов текст и идентификувај ја главната тема/предмет.

Текст:
{content_sample}

Можни предмети се: Математика, Биологија, Историја, Физика, Хемија, Програмирање, Информатика, Литература, Географија, Спорт, Економија, Право, Психологија, Социологија, Филозофија, Уметност, Музика, Медицина, Инженерство.

Инструкции:
- Прочитај го ВНИМАТЕЛНО целиот текст
- Идентификувај ги клучните зборови и теми
- Избери ТОЧНО еден предмет кој најмногу одговара на содржината
- Одговори САМО со името на предметот на македонски јазик (еден збор или два збора)
- Ако не може да се идентификува специфична тема, одговори со "Општо"

Предмет:"""  
        
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": "qwen2.5:7b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Lower temperature for more consistent classification
                    "top_p": 0.8,
                    "num_predict": 20  # Limit response length
                }
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            subject = result.get('response', '').strip()
            
            # Clean up the response - remove quotes, extra punctuation
            subject = re.sub(r'["\'\\.\n\r]', '', subject)
            subject = subject.strip()
            
            # If response is empty or too long (likely not a subject), return General
            if not subject or len(subject) > 50:
                return "Општо"
            
            # Capitalize first letter
            subject = subject[0].upper() + subject[1:] if len(subject) > 1 else subject.upper()
            
            logger.info(f"Classified document subject as: {subject}")
            return subject
        else:
            logger.error(f"Failed to classify document: HTTP {response.status_code}")
            return "Општо"
            
    except Exception as e:
        logger.error(f"Error classifying document subject: {e}")
        return "Општо"
