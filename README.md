# Mapster API & Game Platform

**Mapster** is a geo-guessing game based on **Telegram WebApp**. The goal of the game is to find a location from a given **GoogleStreetView** panorama as close as possible.

The project is designed not just as a game, but as a platform with business-oriented features for player engagement, retention, and data analysis.

The game backend is built with **Django** and **Django Rest Framework**, serving by a lightweight **React** client. 

<img src="https://freeimage.host/i/snimok-ekrana-2025-06-09-115103.FFkQdtn" width="1024">

<img src="https://freeimage.host/i/snimok-ekrana-2025-06-09-115119.FFkQJwX" width="1024">

<img src="https://freeimage.host/i/snimok-ekrana-2025-06-09-115132.FFkQHut" width="1024">

<img src="https://freeimage.host/i/snimok-ekrana-2025-06-09-115138.FFkQ99I" width="1024">

<img src="https://freeimage.host/i/snimok-ekrana-2025-06-09-115142.FFkQ3ns" width="1024">

## Core Product Features

The backend is architected to support key business drivers for a gaming application:

* **Player Engagement & Retention:** The API provides detailed user profiles with statistics (`total_score`, `avg_error`, `avg_time`), fostering competition and a desire for self-improvement.
* **Daily Engagement & Monetization Hooks:** A daily move limit (`daily_moves_remaining`) is tracked per user. This is a classic mobile gaming mechanic that encourages daily logins and provides a clear future monetization point (e.g., "purchase more moves").
* **Competitive Social Platform:** A global leaderboard sorting by multiple filters (total score, games played, average score).
* **Data-Driven Content Balancing:** The system aggregates performance statistics for each game location (`avg_error`, `total_time` per location). This data is invaluable for analyzing location difficulty, balancing gameplay, and curating the user experience.


## Technical Stack

The architecture emphasizes backend robustness, scalability, and modern development practices.

### **Backend**
* **Framework:** Django & Django Rest Framework (DRF)
* **Database:** PostgreSQL (Containerized with Docker)
* **Asynchronous Processing:**
    * **Celery:** Distributed task queue for running background jobs without blocking the API.
    * **Redis:** High-performance in-memory key-value store, used as the message broker for Celery and for caching.
* **Key Libraries:**
    * **Geopy:** Used for highly accurate geospatial distance calculations between coordinates.
* **Authentication:** Token-based authentication (`DRF AuthToken`).

### **Tooling & Code Quality**
* **Testing:** The project is supported by a comprehensive test suite using Django's testing framework to ensure the reliability of business logic and API endpoints.
* **Linting & Formatting:** **Ruff** is used for extremely fast, high-performance code linting and formatting, ensuring code quality and consistency.
* **Package Management:** **uv** is utilized as a modern, high-speed package installer and resolver, significantly faster than traditional tools.

### **Frontend (Client)**
* **Library:** React
* **API Communication:** `axios` for asynchronous API calls.
* **Mapping Services:** Google Maps API via `@react-google-maps/api`.

## Backend Architecture & Key Implementations

* **RESTful API Design:** The API is built using DRF's `APIView` and `Serializers` for robust validation of all incoming data and well-structured JSON responses. This ensures a clean and stable contract between the backend and any client.

* **Geospatial Logic:** The core scoring algorithm leverages the **Geopy** library to accurately calculate the great-circle distance between the user's guess and the actual location, forming the basis of the game's primary metric.

* **Third-Party Service Integration:**
    * **Google Maps API:** The backend is designed to process and validate location data, which can include parsing Google Street View URLs to extract coordinates and other metadata, creating a streamlined content pipeline.
    * **Telegram Authentication:** A dedicated endpoint handles authentication via the Telegram Web App protocol, validating user data and issuing a session token.

* **Asynchronous Architecture:** The integration of **Celery** and **Redis** makes the platform highly scalable. It allows for offloading potentially long-running or periodic tasks (e.g., recalculating daily move limits, updating aggregate leaderboard stats) to a background worker queue, ensuring the main API remains fast and responsive under load.

* **Testing:** A commitment to quality is ensured through a suite of automated **tests**. This includes unit tests for critical business logic and integration tests for API endpoints to verify request/response contracts, authentication, and permissions.

## Local Setup & Installation

1.  Clone the repository: `git clone https://github.com/stoboal/mapster.git`
2.  Navigate to the project directory.
3.  Create a `.env` file from the `.env.example` template and populate it with your configuration.
4.  Build and run the containers: `docker-compose up --build`
5.  The API will be available at `http://localhost:8000`.