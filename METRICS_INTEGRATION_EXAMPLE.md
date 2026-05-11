# LLM Metrics Integration Examples

This document shows how to integrate LLM metrics tracking into your services.

## Basic Usage

### Tracking LLM Requests

```python
import time
from infrastructure.monitoring.llm_metrics import LLMMetricsTracker

# In your chat or LLM service
start_time = time.time()

try:
    # Make LLM request
    response = llm_client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        max_tokens=1000
    )
    
    elapsed = time.time() - start_time
    
    # Track metrics
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    
    # Example pricing for GPT-4
    input_cost = input_tokens * 0.00003
    output_cost = output_tokens * 0.00006
    
    LLMMetricsTracker.track_request(
        user_id=user_id,
        model="gpt-4",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        response_time=elapsed
    )
    
except Exception as e:
    LLMMetricsTracker.track_error(
        user_id=user_id,
        model="gpt-4",
        error=str(e)
    )
    raise
```

## Model Pricing Reference

### OpenAI Models
- **GPT-4**
  - Input: $0.00003 per token
  - Output: $0.00006 per token

- **GPT-3.5-turbo**
  - Input: $0.0005 per 1K tokens
  - Output: $0.0015 per 1K tokens

- **Claude (via API)**
  - Input: $0.0008 per 1K tokens
  - Output: $0.0024 per 1K tokens

### Groq Models (typically cheaper)
- **Mixtral-8x7b**: ~$0.27 per million input tokens
- **Llama2-70b**: ~$0.70 per million input tokens

## Integration with Chat Service

Here's an example of integrating metrics into the ChatService:

```python
import time
import structlog
from infrastructure.monitoring.llm_metrics import LLMMetricsTracker
from domain.ports.llm_port import LLMPort

logger = structlog.get_logger()

class ChatService:
    def __init__(self, llm_port: LLMPort):
        self._llm_port = llm_port
    
    async def generate_response(
        self,
        system_prompt: str,
        messages: list,
        user_id: str,  # Track which user
        model: str = "gpt-4"
    ):
        start_time = time.time()
        
        try:
            llm_response = await self._llm_port.generate_response(
                system_prompt=system_prompt,
                messages=messages,
            )
            
            elapsed = time.time() - start_time
            
            # Track metrics if response contains usage info
            if hasattr(llm_response, 'tokens_used'):
                input_tokens = llm_response.tokens_used.get('input', 0)
                output_tokens = llm_response.tokens_used.get('output', 0)
                
                # Calculate cost based on model
                cost = self._calculate_cost(model, input_tokens, output_tokens)
                
                LLMMetricsTracker.track_request(
                    user_id=user_id,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    input_cost=cost['input'],
                    output_cost=cost['output'],
                    response_time=elapsed
                )
            
            logger.info(
                "chat_service.generate_response.completed",
                user_id=user_id,
                model=model,
                elapsed_seconds=elapsed
            )
            
            return llm_response
            
        except Exception as e:
            LLMMetricsTracker.track_error(
                user_id=user_id,
                model=model,
                error=str(e)
            )
            raise
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int):
        """Calculate cost based on model pricing."""
        pricing = {
            'gpt-4': {'input': 0.00003, 'output': 0.00006},
            'gpt-3.5-turbo': {'input': 0.0005 / 1000, 'output': 0.0015 / 1000},
            'claude': {'input': 0.0008 / 1000, 'output': 0.0024 / 1000},
        }
        
        rates = pricing.get(model, {'input': 0, 'output': 0})
        
        return {
            'input': input_tokens * rates['input'],
            'output': output_tokens * rates['output']
        }
```

## Querying the Metrics

### Grafana Queries

#### Total Cost Per User (Last Hour)
```promql
sum by (user_id) (increase(llm_request_cost_total[1h]))
```

#### Average Tokens Per Request
```promql
avg(llm_tokens_per_request_bucket)
```

#### Most Used Models
```promql
topk(5, sum by (model) (rate(llm_tokens_used_total[1h])))
```

#### Cost by User (Pie Chart)
```promql
sum by (user_id) (llm_request_cost_total)
```

#### Token Budget Tracking
```promql
sum by (user_id) (llm_tokens_used_total)
```

### Logs with Loki

#### Find LLM Responses for Specific User
```logql
{job="socratic-ai"} | json | user_id="user-123" | event="llm_request_completed"
```

#### Track Failed LLM Requests
```logql
{job="socratic-ai"} | json | level="ERROR" | event="llm_request_failed"
```

#### High-Cost Requests
```logql
{job="socratic-ai"} | json | total_cost > 0.01
```

## Usage Patterns

### 1. Real-time Cost Monitoring
Monitor spending in real-time:
```promql
rate(llm_request_cost_total[1m])
```

### 2. Per-User Quotas
Check if users exceed their token budget:
```promql
sum by (user_id) (llm_tokens_used_total) > 100000
```

### 3. Model Performance Comparison
Compare latency between different models:
```promql
histogram_quantile(0.95, rate(llm_response_duration_seconds_bucket[5m]))
```

### 4. Cost Efficiency Analysis
Analyze cost per token:
```promql
sum by (model) (increase(llm_request_cost_total[1d])) / 
sum by (model) (increase(llm_tokens_used_total[1d]))
```

## Best Practices

1. **Always track metrics in try-catch blocks**
   - Use `track_error()` for failures
   - Provides complete observability

2. **Use meaningful user IDs**
   - Track by user, organization, or account
   - Enables cost allocation

3. **Include model name**
   - Compare performance across models
   - Identify cost optimization opportunities

4. **Measure elapsed time accurately**
   - Start timer before LLM call
   - Stop after receiving response

5. **Calculate costs correctly**
   - Use accurate pricing from provider
   - Account for both input and output tokens
