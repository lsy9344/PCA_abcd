# PCA_abcd Project - Qwen Code Context

## Project Overview

This is a parking coupon automation system that automatically logs into parking websites, searches for vehicles by license plate number, and applies optimal discount coupons based on each store's policies. The system is built using Clean Architecture principles with a strong emphasis on domain-driven design and separation of concerns.

### Key Features
- **Multi-store Support**: Currently supports 4 different parking stores (A, B, C, D)
- **Web Automation**: Uses Playwright for browser automation to interact with parking websites
- **Dynamic Coupon Calculation**: Applies optimal coupons based on target discount hours and available coupons
- **Lambda Deployment**: Designed for AWS Lambda deployment with containerized environment
- **Structured Logging**: Uses JSON-formatted logging for better monitoring and debugging
- **Telegram Notifications**: Sends alerts for failures and important events

## Architecture

The project follows Clean Architecture with these main layers:

```
parking_automation/
├── core/                           # Core domain logic
│   ├── domain/                     # Domain layer (models, repositories)
│   └── application/                # Application layer (use cases, DTOs)
├── infrastructure/                 # Infrastructure layer
│   ├── config/                     # Configuration management
│   ├── web_automation/             # Web automation (Playwright)
│   ├── notifications/              # Notification system
│   ├── logging/                    # Logging system
│   └── factories/                  # Factory patterns
├── interfaces/                     # Interface layer
│   └── api/                        # API endpoints (Lambda)
├── shared/                         # Shared components
│   ├── exceptions/                 # Custom exceptions
│   └── utils/                      # Utilities
└── stores/                         # Store-specific routing
```

### Core Components

1. **Domain Layer**: Contains core business models like Store, Coupon, Vehicle, and repository interfaces
2. **Application Layer**: Contains use cases like ApplyCouponUseCase that orchestrate business logic
3. **Infrastructure Layer**: Implements concrete adapters for web automation, notifications, logging, etc.
4. **Interfaces Layer**: Provides entry points (Lambda handlers) for the application

## Key Technologies

- **Python 3.12**: Primary programming language
- **Playwright**: Web automation framework for browser interactions
- **AWS Lambda**: Serverless deployment target
- **PyYAML**: Configuration management
- **Loguru**: Structured logging
- **Docker**: Containerization for consistent deployment

## Configuration Structure

Each store has its own YAML configuration file in `infrastructure/config/store_configs/`:

- `a_store_config.yaml`: Configuration for Store A (동탄점)
- `b_store_config.yaml`: Configuration for Store B
- `c_store_config.yaml`: Configuration for Store C
- `d_store_config.yaml`: Configuration for Store D

Configuration includes:
- Store credentials and URLs
- Coupon definitions and selectors
- Web element selectors for automation
- Discount policies for weekdays/weekends

## Main Entry Points

### Lambda Handler
- `interfaces/api/lambda_handler.py`: Main AWS Lambda entry point
- Accepts `store_id` and `vehicle_number` parameters
- Routes to appropriate store crawler based on store ID

### Store-Specific Lambda Files
- `interfaces/api/lambda_a.py`: Lambda handler for Store A
- `interfaces/api/lambda_b.py`: Lambda handler for Store B
- `interfaces/api/lambda_c.py`: Lambda handler for Store C
- `interfaces/api/lambda_d.py`: Lambda handler for Store D

## Key Classes and Components

### AutomationFactory
Located in `infrastructure/factories/automation_factory.py`:
- Creates all components needed for automation
- Manages singleton instances of loggers and notification services
- Instantiates store-specific crawlers based on store ID

### Store Crawlers
Located in `infrastructure/web_automation/store_crawlers/`:
- `AStoreCrawler`: Implements web automation for Store A
- `BStoreCrawler`: Implements web automation for Store B
- `CStoreCrawler`: Implements web automation for Store C
- `DStoreCrawler`: Implements web automation for Store D

Each crawler implements:
- `login()`: Authenticates to the parking website
- `search_vehicle()`: Searches for a vehicle by license plate
- `get_coupon_history()`: Retrieves available coupons and usage history
- `apply_coupons()`: Applies calculated coupons to the vehicle
- `cleanup()`: Cleans up browser resources

### DiscountCalculator
Located in `core/domain/models/discount_policy.py`:
- Calculates optimal coupon combinations based on target discount hours
- Considers existing coupon usage history
- Applies different strategies for weekdays vs weekends

### ConfigManager
Located in `infrastructure/config/config_manager.py`:
- Loads and manages all configuration files
- Provides store-specific configurations
- Manages Playwright, Telegram, and logging configurations

## Deployment Process

### Docker Deployment
The project includes a Dockerfile that:
1. Uses AWS Lambda Python 3.12 base image
2. Installs required system libraries for Playwright
3. Installs Python dependencies
4. Installs Playwright Chromium browser
5. Copies application code
6. Sets up Lambda handler

### Lambda Deployment
- Each store has its own Lambda function for independent scaling
- Lambda handler routes requests to appropriate store crawler
- Environment is containerized for consistency

## Development Setup

### Prerequisites
1. Python 3.12
2. Playwright dependencies

### Installation Steps
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

### Testing
Unit and integration tests are located in the `tests/` directory:
```bash
# Run all tests
python -m pytest

# Run unit tests only
python -m pytest tests/unit/

# Run integration tests only
python -m pytest tests/integration/
```

## Adding New Stores

To add a new store (e.g., Store E):

1. Create configuration file: `infrastructure/config/store_configs/e_store_config.yaml`
2. Implement crawler: `infrastructure/web_automation/store_crawlers/e_store_crawler.py`
3. Add to store router: Update `stores/store_router.py` with new store mapping
4. Create Lambda handler: `interfaces/api/lambda_e.py`
5. Add to factory: Update `infrastructure/factories/automation_factory.py`
6. Write tests: Create test cases in `tests/` directory

## Error Handling and Logging

The system uses structured logging with different error codes:
- `FAIL_AUTH`: Authentication failures
- `NO_VEHICLE`: Vehicle not found
- `FAIL_SEARCH`: Search failures
- `FAIL_PARSE`: Parsing failures
- `FAIL_APPLY`: Coupon application failures

Logs are formatted as JSON for better parsing and monitoring. Telegram notifications are sent for critical failures.

## Performance Considerations

- Browser instances are reused within Lambda containers for better performance
- Settings and logger instances are cached
- CloudWatch logging costs are optimized by reducing verbose logging in production