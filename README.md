# OmniScrape Suite (Scrappers All-in-One)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15.0-black.svg)](https://nextjs.org)
[![Playwright](https://img.shields.io/badge/Playwright-1.44.0-blue.svg)](https://playwright.dev/python/)

A multi-platform business data scraper and real-time dashboard. Features a Next.js frontend and a FastAPI backend with WebSockets to run and monitor scrapers for websites, Google Maps, Facebook, Instagram, and LinkedIn, supporting structured data exports to Excel, Word, and PDF.

## 🚀 Features

- **Real-Time Job Monitoring**: Watch logs and progress percentages live over WebSockets.
- **Master Orchestrator**: Input a website URL, detect its associated social platforms, and run sub-scrapers automatically.
- **6 Built-in Scraper Modules**:
  1. **General Orchestrator**: Aggregates website, social links, and runs platform scrapers in parallel.
  2. **Website Crawler**: Recursively extracts metadata, headings, body text, emails, phones, schema.org markup, and documents.
  3. **Google Maps**: Gathers business profiles, ratings, review feeds (with sorting/pagination), and owner replies.
  4. **Instagram**: Public profile metrics (followers, posts) and post details (captions, tags).
  5. **LinkedIn**: Collects company profile description, job openings, and public posts.
  6. **Facebook**: Public page info, events, reviews, and post contents.
- **Rich Document Exports**: Support for Excel sheets, PDF summaries, and Microsoft Word formats.

## 🛠️ Architecture

The project splits into a Next.js web application and a FastAPI python service:

```mermaid
graph TD
    UI[Next.js Frontend] -->|REST API| API[FastAPI Backend]
    UI -->|WebSocket| WS[FastAPI WebSocket Endpoint]
    API -->|Async Tasks| Workers[Async Python Workers]
    Workers -->|Playwright / BeautifulSoup| Web[Target Webpages & Social Media]
    Workers -->|Store Jobs/Results| DB[(SQLite Database)]
    Workers -->|Stream Progress/Logs| WS
```

## 📦 Directory Structure

```
├── backend/
│   ├── app/
│   │   ├── models/        # Database models
│   │   ├── routers/       # API route handlers (scrape, jobs, results, exports, logs)
│   │   ├── schemas/       # Pydantic validation schemas
│   │   ├── scrapers/      # Playwright Scraper modules (base, general, website, google_maps, facebook, etc.)
│   │   ├── main.py        # FastAPI entrypoint
│   │   └── database.py    # SQLite connections
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/           # App router pages (dashboard layout, custom scraper views)
│   │   ├── components/    # Reusable UI widgets & job tracker panels
│   │   └── hooks/         # React hooks (WebSocket feed client)
│   └── package.json
└── docker-compose.yml
```

## 🚦 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Google Chrome / Playwright Webkit installed**

### Backend Setup

1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browser binaries:
   ```bash
   playwright install chromium
   ```
4. Copy the environment template and edit parameters if needed:
   ```bash
   cp .env.example .env
   ```
5. Run the development server:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   The API documentation will be available at `http://127.0.0.1:8000/api/docs`.

### Frontend Setup

1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` to interact with the dashboard.

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
