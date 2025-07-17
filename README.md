 # CupBet - Django Betting Platform

## Project Outline

CupBet is a peer-to-peer betting platform built with Django. It allows users to:
- View upcoming and recent matches
- Place bets on matches (with Paystack integration)
- Track bet status using a unique bet code
- Claim payouts for winning bets (manual admin processing)
- Admin features for managing matches, bets, payouts, and house fees

### Main Features
- User registration via bet placement (name, email)
- Paystack payment integration for secure deposits
- Bet code generation for tracking
- Admin dashboard for match and payout management
- Payout claim form with bank verification
- House fee calculation and tracking

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd cupbet
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv betenv
   betenv\Scripts\activate  # On Windows
   # or
   source betenv/bin/activate  # On Mac/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   - Create a `.env` file in the `cupbet` directory with:
     ```env
     PAYSTACK_SECRET_KEY=your_paystack_secret_key
     ```

5. **Apply migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser for admin access:**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

8. **Access the app:**
   - User: http://127.0.0.1:8000/
   - Admin: http://127.0.0.1:8000/admin/

## Usage
- Place bets on upcoming matches from the home page.
- After payment, receive a bet code for tracking.
- Use the "Check Bet" page to view bet status.
- If you win, claim payout by submitting your bank details.
- Admin reviews and processes payouts via the admin dashboard.

## TODO / Future Improvements
- Add user authentication and profiles
- Automated payout processing via Paystack
- Email notifications for bet status and payouts
- Mobile-friendly UI/UX improvements
- Add support for more payment gateways
- Real-time match updates and results
- Enhanced reporting and analytics for admin
- Multi-language and multi-currency support
- Unit and integration tests for critical flows

## Production Deployment Suggestions
- Set `DEBUG = False` in `settings.py`
- Add your domain to `ALLOWED_HOSTS`
- Use a production-ready database (e.g., PostgreSQL)
- Serve static and media files via a CDN or web server
- Use HTTPS and secure your secret keys
- Set up proper logging and monitoring
- Regularly back up your database

---

For questions or contributions, please open an issue or pull request.
