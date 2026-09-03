> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Баланс

> Запрос текущего баланса аккаунта

## Примеры

```bash theme={null}
curl "https://speshu.ai/api/v1/balance" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

```python theme={null}
import requests

response = requests.get(
    'https://speshu.ai/api/v1/balance',
    headers={'Authorization': 'Bearer YOUR_API_KEY'}
)

data = response.json()
print(f"Баланс: {data['RUB']} руб.")
```

```javascript theme={null}
const response = await fetch('https://speshu.ai/api/v1/balance', {
  headers: { 'Authorization': 'Bearer YOUR_API_KEY' }
});

const data = await response.json();
console.log(`Баланс: ${data.RUB} руб.`);
```

## Ответ (200)

```json theme={null}
{
  "RUB": "9.28591714"
}
```

| Поле  | Тип    | Описание                |
| ----- | ------ | ----------------------- |
| `RUB` | string | Текущий баланс в рублях |

## Мониторинг баланса

```python theme={null}
import requests
import time

def check_balance(api_key, min_balance=100):
    response = requests.get(
        'https://speshu.ai/api/v1/balance',
        headers={'Authorization': f'Bearer {api_key}'}
    )

    data = response.json()
    balance = float(data['RUB'])

    if balance < min_balance:
        print(f"Внимание! Баланс низкий: {balance} руб.")

    return balance

# Проверка каждый час
while True:
    balance = check_balance('YOUR_API_KEY')
    print(f"Текущий баланс: {balance} руб.")
    time.sleep(3600)
```

Пополнить баланс можно в консоли через банковскую карту, СБП или счёт для юридических лиц.


## OpenAPI

````yaml GET /v1/balance
openapi: 3.0.0
info:
  title: SpeShu.AI API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://speshu.ai/api
    description: Production
security:
  - bearer: []
tags: []
paths:
  /v1/balance:
    get:
      tags:
        - V1Legacy
      operationId: V1LegacyController_getUserBalance[1]
      parameters: []
      responses:
        '200':
          description: ''
components:
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <SPESHU_AI_API_KEY>

````