<h1 align="center">Student ERP</h1>

<p align="center">
  A Flask backend for a college's admissions, fees, hostel and library.<br />
  Every module is a JSON API, and staff see live numbers on a dashboard.
</p>

Student ERP takes a student from application to enrollment. An applicant posts to the admission API and gets an application ID. Staff review the application and approve it. The approval creates the student with a roll number built from the admission year, the course code and a four-digit serial, then emails the applicant. From there an admin bills the student's fees for a semester, the hostel allocates a room, and the library issues books. Each step is an endpoint.

This repo is the backend only. There is no frontend, so you call the API from an HTTP client or your own app. It runs on Flask and SQLAlchemy and uses SQLite until you point it at another database. Redis is optional. Emails need an SMTP account.

## What you get

- **Applications become student records.** `POST /api/admission/apply` returns an `application_id`. A staff member moves it to `under_review`, `approved`, `declined` or `waitlisted`. An approval creates the `Student` row with a generated roll number and sends the applicant an email.
- **Fees are billed by semester and paid as PDFs.** An admin posts a semester from 1 to 8, an academic year and a list of course IDs to `/api/fee/generate-demand`. Each fee is due 30 days out unless you pass `due_days`. A payment produces a PDF receipt with a QR code, and anyone with the receipt number can download it from `/api/fee/receipt-download/<receipt_number>`.
- **Library loans have hard limits.** A student can hold five books at once and cannot take another while a book is overdue. A renewal adds 14 days unless the request says otherwise.
- **Routes check the token and the role.** Login returns an access token that lasts 24 hours and a refresh token that lasts 30 days. Admin and staff routes check the role after the token is verified. Other routes need a valid token. Login, applying, the application status lookup, the receipt download, the health checks and the two dashboard charts need no token.
- **Student changes leave an audit trail.** Creating, updating, deactivating or bulk-changing a student writes a line to `logs/admin_actions.log`.
- **Failed emails are retried in the background.** Sends run on their own threads. A failed send goes to a queue and is retried up to three times, after 60, 120 and 180 seconds.
- **The dashboard updates over Socket.IO.** Clients connect to the `/dashboard` namespace with a JWT in the connection payload and join a room for their role. Admission decisions and payments push updates to connected dashboards. A client can send `request_stats` to get the current counts.
- **Requests are rate limited and filtered.** Each IP gets 100 requests a minute, or 10 every five minutes on auth routes. Over the limit, the API returns 429. Requests whose input matches SQL keywords or script patterns get a 400. Responses carry a Content-Security-Policy and `X-Frame-Options: DENY`. Counters live in each process's memory, so two worker processes count separately.

## Running it

The code runs on Python 3.12. Pillow 10.0.1, pinned in `requirements.txt`, does not build on Python 3.14, so `pip install` fails there.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

The app creates its tables on startup. In development it also creates `instance/student_erp_dev.db` and a `logs/` folder in the working directory. It listens on port 5000. Set `PORT` to change that.

Run it from a terminal. Flask-SocketIO refuses to start its Werkzeug server when stdin is not a terminal, so a systemd unit or a container exits at startup. This repo has no WSGI server setup, so you add one yourself.

Check that it is up:

```sh
curl http://localhost:5000/api/auth/health
```

The app does not read `.env` files. Export the variables in your shell. `.env.example` names several variables the code never reads, so use the table below.

## Configuration

| Variable | Default | What it sets |
| --- | --- | --- |
| `FLASK_ENV` | `development` | Config to load: `development`, `testing` or `production`. `run.py` turns on debug mode when it is `development`. |
| `PORT` | `5000` | Port `run.py` listens on. |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask secret key. |
| `JWT_SECRET_KEY` | `jwt-secret-string` | Signs JWT tokens. |
| `DEV_DATABASE_URL` | `sqlite:///student_erp_dev.db` | Database in development. |
| `DATABASE_URL` | `sqlite:///student_erp.db` | Database in production. The production default is a MySQL URL, and `requirements.txt` has no MySQL driver. |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` | `localhost`, `6379`, `0` | Redis connection. The app pings it at startup and runs without it. |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins. |
| `MAIL_SERVER`, `MAIL_PORT` | `smtp.gmail.com`, `587` | SMTP host and port. |
| `MAIL_USE_TLS` | `true` | Use TLS for the SMTP connection. |
| `MAIL_USERNAME`, `MAIL_PASSWORD` | none | SMTP login. |
| `MAIL_DEFAULT_SENDER` | none | From address. Sends fail without it. |

The defaults for `SECRET_KEY` and `JWT_SECRET_KEY` are placeholders from the source. Set both before you run the app anywhere other people can reach.

The fee receipt header prints "Government Engineering College", a string hardcoded in `app/routes/fee.py`. Change it before you issue receipts for another institution.

## API

| Prefix | Module | Covers |
| --- | --- | --- |
| `/api/auth` | `app/routes/auth.py` | Login, refresh, logout, profile, password change, token check. |
| `/api/student` | `app/routes/student.py` | Create, read, update and deactivate students, search, statistics, academic record, fee and library history, bulk operations. |
| `/api/admission` | `app/routes/admission.py` | Apply, list applications, process, status lookup, statistics. |
| `/api/fee` | `app/routes/fee.py` | Fee demands, payments, pending fees, receipts, reports, statistics. |
| `/api/hostel` | `app/routes/hostel.py` | Available rooms, allocate, vacate, occupancy report, student lookup, statistics. |
| `/api/library` | `app/routes/library.py` | Books, issue, return, renew, overdue, search, categories, statistics. |
| `/api/dashboard` | `app/routes/dashboard.py` | Summary, enrollment and fee charts, and the Socket.IO namespace `/dashboard`. |

The Swagger UI runs at `/api/v1/docs/`, but its paths do not match the routes above. It lists `/fees/structure`, for example, and no route with that path exists. Use this table.

## Testing

Run the suite from the repo root:

```sh
pytest
```

`tests/test_final_backend_verification.py` imports `requests`, which `requirements.txt` does not install, so pytest stops at collection. Skip that file to run the rest:

```sh
pytest --ignore=tests/test_final_backend_verification.py
```

At the time of this rewrite, that command reported 117 passed, 18 failed, 2 errors and 4 skipped. The failures are in `tests/test_fee_management.py` and `tests/test_data_security_validation.py`.

## License

Released under the [MIT License](LICENSE).
