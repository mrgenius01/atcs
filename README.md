# Secure ATCS MVP - Automated Toll Collection System

A Minimal Viable Product for a Secure Automated Toll Collection System (ATCS) using ANPR, secure payments, and immutable audit trails, tailored for Zimbabwe.

## 🎯 MVP Features

### Core Modules
- **ANPR**: Simulated license plate recognition (Zimbabwe format: AB·123CD)
- **Payments**: Simulated EcoCash API integration with prepaid account validation
- **Logging**: Transaction storage with AES-256-GCM encryption for sensitive data
- **Blockchain**: File-based audit trail simulation (ready for Hyperledger Fabric)
- **Dashboard**: Django admin interface with RBAC and TOTP MFA support
- **Security**: Encryption utilities and IDS monitoring placeholders

### Technology Stack
- **Backend**: Django 5.0.7 + SQLite (production-ready for PostgreSQL)
- **Authentication**: TOTP-based MFA via pyotp
- **Encryption**: AES-256-GCM for sensitive field encryption
- **Testing**: pytest with Django integration

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git

### Installation & Setup

```powershell
# Clone and navigate to project
git clone <your-repo-url>
cd secure-atcs

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python src/manage.py migrate

# Create admin user
python src/manage.py createsuperuser

# Start development server
python src/manage.py runserver
```

### Access Points
- **Main Dashboard**: http://localhost:8000/
- **Admin Interface**: http://localhost:8000/admin/
- **API Endpoint**: http://localhost:8000/api/transactions/

## 🧪 Testing

```powershell
# Run all tests
python -m pytest -v

# Run specific module tests
python -m pytest tests/test_anpr.py -v
python -m pytest tests/test_payments.py -v
python -m pytest tests/test_security.py -v
```

## 📁 Project Structure

```
secure-atcs/
├── src/                     # Django application
│   ├── anpr/               # License plate recognition (simulated)
│   ├── payments/           # EcoCash integration (simulated)
│   ├── blockchain/         # Audit trail (file-based simulation)
│   ├── dashboard/          # Web interface & admin views
│   ├── security/           # Encryption & auth utilities
│   ├── settings.py         # Django configuration
│   └── manage.py           # Django management script
├── tests/                  # Unit tests
├── scripts/                # PowerShell deployment scripts
├── data/                   # Sample data & model placeholders
└── docs/                   # Documentation
```

## 💡 MVP Limitations & Future Enhancements

### Current MVP (Simulated)
- ✅ ANPR returns Zimbabwe-format plates (AB·123CD)
- ✅ EcoCash API simulation (85% success rate)
- ✅ File-based blockchain audit trail
- ✅ SQLite database (no external dependencies)
- ✅ TOTP MFA framework (demo-ready)

### Production Roadmap
- 🔜 Replace ANPR simulation with TensorFlow model + OpenCV
- 🔜 Integrate real EcoCash/OneMoney APIs
- 🔜 Deploy Hyperledger Fabric network
- 🔜 PostgreSQL database with connection pooling
- 🔜 Docker containerization & Kubernetes deployment
- 🔜 Snort IDS integration
- 🔜 TLS 1.3 reverse proxy (Caddy/Nginx)

## 🔒 Security Features

- **Encryption**: AES-256-GCM for sensitive data at rest
- **Authentication**: Django's built-in auth + TOTP MFA
- **Audit Trail**: Immutable hash chain (blockchain simulation)
- **Access Control**: Role-based permissions via Django groups
- **Data Protection**: Compliant with Zimbabwe Data Protection Act 2021

## 📊 Transaction Flow

1. **Vehicle Detection**: Simulated ANPR captures plate number
2. **Payment Processing**: EcoCash account validation & deduction
3. **Audit Logging**: Transaction stored with encrypted sensitive fields
4. **Blockchain Hash**: Immutable audit hash appended to ledger
5. **Dashboard Update**: Real-time transaction display

## 🛠️ Development Notes

- Uses SQLite by default for easy local development
- All heavy dependencies (TensorFlow, OpenCV) replaced with lightweight stubs
- TOTP secrets are randomly generated per session (demo purposes)
- Blockchain ledger writes to local `audit_ledger.txt` file
- Payment API returns 85% success rate for realistic simulation

## 📝 Environment Configuration

Copy `.env.example` to `.env` and customize:

```bash
DEBUG=True
SECRET_KEY=your-secret-key-here
USE_POSTGRES=False  # Set to True for PostgreSQL
FIELD_ENCRYPTION_KEY=your-32-byte-hex-key
TOTP_ISSUER=SecureATCS
```

## 🎓 Academic Use

This MVP is designed for dissertation defense and academic evaluation. It demonstrates:
- System architecture and component integration
- Security best practices implementation
- Scalable design patterns for future expansion
- Compliance with data protection regulations

## 📄 License

For academic MVP use. Review dependencies' licenses before production deployment.
