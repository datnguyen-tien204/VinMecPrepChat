# VinmecPrep AI - Huong dan su dung Backend API (Kafka)

Tai lieu nay tong hop cach chay va test backend API cho project `VinMec-v2-kafka`.

## 0) API base URL

- Base URL (host): `http://localhost:6666`
- Content-Type: `application/json`
- Luu y: API chay trong container port `8000`, duoc expose ra host port `6666`.

## 1) Chay backend stack

```powershell
cd E:\Working\VinUni-FinalProj\VinMec-v2-kafka
Copy-Item .env.example .env
# `.env.example` la file mau chuan duy nhat; sua `.env` de chay that

docker compose up -d --build
```

Kiem tra nhanh:

```powershell
docker compose ps
```

Ban nen thay service `api` co dang:

- `127.0.0.1:6666->8000/tcp`

## 2) Endpoints chinh

### 2.1 Health check

- Method: `GET`
- URL: `http://localhost:6666/health`

Response:

```json
{
  "status": "ok",
  "redis": true
}
```

### 2.2 Chat (sync)

- Method: `POST`
- URL: `http://localhost:6666/chat`

Request:

```json
{
  "message": "Xet nghiem mau tong quat can nhin an khong?",
  "session_id": "",
  "history": []
}
```

Response:

```json
{
  "reply": "...",
  "session_id": "8935cba4-9721-4d0f-a2e6-df0a256bd7ae",
  "job_id": "7e7cf996-dfce-4289-b491-f10242ffad8b",
  "blocked": false,
  "guard_result": "pass"
}
```

Giai thich nhanh:

- `message`: bat buoc, 1-2000 ky tu
- `session_id`: de trong lan dau, lan sau gui lai de giu context
- `history`: tuy chon; de `[]` de backend dung lich su trong Redis

### 2.3 Chat async (non-blocking)

- Method: `POST`
- URL: `http://localhost:6666/chat/async`

Request body giong `/chat`.

Response mau:

```json
{
  "job_id": "57f60d14-c6af-44e1-87af-aef7efc98f74",
  "session_id": "8935cba4-9721-4d0f-a2e6-df0a256bd7ae",
  "status": "queued"
}
```

Lay ket qua:

- Method: `GET`
- URL: `http://localhost:6666/chat/result/{job_id}`

Neu chua xong:

```json
{
  "status": "processing",
  "job_id": "..."
}
```

Neu da xong:

```json
{
  "status": "done",
  "job_id": "...",
  "session_id": "...",
  "reply": "...",
  "blocked": false,
  "guard_result": "pass"
}
```

## 3) Feedback APIs

### 3.1 Feedback theo turn (like/dislike)

- Method: `POST`
- URL: `http://localhost:6666/feedback`

Request:

```json
{
  "session_id": "8935cba4-9721-4d0f-a2e6-df0a256bd7ae",
  "rating": "like",
  "comment": "Tra loi ro rang, de hieu"
}
```

Response:

```json
{
  "uuid": "12c264cc-fb53-4075-908b-ad00ddb045b2",
  "session_id": "8935cba4-9721-4d0f-a2e6-df0a256bd7ae",
  "rating": "like",
  "saved": true
}
```

Luu y:

- `rating` chi nhan: `like` hoac `dislike`
- Neu session het han/khong ton tai -> co the tra `404`

### 3.2 Feedback cuoi phien (1-5 sao)

- Method: `POST`
- URL: `http://localhost:6666/feedback/end`

Request:

```json
{
  "session_id": "8935cba4-9721-4d0f-a2e6-df0a256bd7ae",
  "rating": 5,
  "comment": "Rat huu ich",
  "tags": ["helpful", "accurate"]
}
```

Response:

```json
{
  "uuid": "730b7564-235c-4296-9ca9-78bf2d860c7c",
  "session_id": "8935cba4-9721-4d0f-a2e6-df0a256bd7ae",
  "rating": 5,
  "saved": true
}
```

## 4) Trainer APIs (can X-Trainer-Key)

Cac API duoi day yeu cau header:

- `X-Trainer-Key: <TRAINER_API_KEY>`

Neu key sai -> `403`.
Neu chua cau hinh `TRAINER_API_KEY` -> `503`.

### 4.1 Lay danh sach feedback turn

- `GET /feedback?rating=like&limit=50&offset=0`

### 4.2 Tim semantic feedback turn

- `GET /feedback/search?q=nhin%20an&rating=like&limit=20`

### 4.3 Thong ke feedback turn

- `GET /feedback/stats`

### 4.4 Lay danh sach feedback cuoi phien

- `GET /feedback/end?rating=5&limit=50&offset=0`

### 4.5 Thong ke feedback cuoi phien

- `GET /feedback/end/stats`

## 5) Huong dan Postman (goi y nhanh)

### A. Tao environment

1. Tao Environment moi.
2. Tao bien:
   - `base_url` = `http://localhost:6666`
   - `session_id` = (de trong)
   - `trainer_key` = (neu can test trainer API)

### B. Request thu tu de test full flow

1. `GET {{base_url}}/health`
2. `POST {{base_url}}/chat` (lan dau, `session_id` rong)
3. Copy `session_id` trong response -> luu vao env `session_id`
4. `POST {{base_url}}/feedback` voi `session_id={{session_id}}`
5. `POST {{base_url}}/feedback/end` voi `session_id={{session_id}}`
6. (Trainer) `GET {{base_url}}/feedback/stats` + header `X-Trainer-Key: {{trainer_key}}`

## 6) Test nhanh bang PowerShell

### Health

```powershell
Invoke-RestMethod -Uri "http://localhost:6666/health" -Method Get
```

### Chat sync

```powershell
$body = '{"message":"Toi can chuan bi gi truoc khi den kham?","session_id":"","history":[]}'
Invoke-RestMethod -Uri "http://localhost:6666/chat" -Method Post -ContentType "application/json" -Body $body
```

### Feedback turn

```powershell
$body = '{"session_id":"<SESSION_ID>","rating":"like","comment":"on"}'
Invoke-RestMethod -Uri "http://localhost:6666/feedback" -Method Post -ContentType "application/json" -Body $body
```

### Feedback end

```powershell
$body = '{"session_id":"<SESSION_ID>","rating":5,"comment":"rat huu ich","tags":["helpful"]}'
Invoke-RestMethod -Uri "http://localhost:6666/feedback/end" -Method Post -ContentType "application/json" -Body $body
```

## 7) Ma loi thuong gap

- `422`: sai schema request (thieu field, sai type)
- `403`: trainer key sai
- `404`: khong tim thay session history
- `409`: feedback trung session (mot so case)
- `429`: vuot rate limit
- `500`: loi noi bo
- `503`: service tam thoi khong kha dung / trainer key chua cau hinh
- `504`: chat timeout khi cho ket qua tu queue

Format loi:

```json
{
  "detail": "Noi dung loi"
}
```

## 8) Ghi chu van hanh

- API docs UI (`/docs`, `/redoc`) dang tat.
- Neu vua restart stack, app se warmup ket noi embedding API luc khoi dong.
- De nap du lieu y te vao Weaviate:

```powershell
cd E:\Working\VinUni-FinalProj\VinMec-v2-kafka
python .\scripts\ingest_medical_data.py --reset
python .\scripts\ingest_medical_data.py --verify
```

---

Chuc ban test API muot nhu lua. Neu can, co the bo sung them Postman Collection mau cho team import la chay ngay.
