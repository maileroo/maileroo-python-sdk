# Maileroo Python SDK

[Maileroo](https://maileroo.com) is a robust email delivery platform designed for effortless sending of transactional and marketing emails.  
This Python SDK offers a straightforward interface for working with the Maileroo API, supporting basic email formats, templates, bulk sending, and scheduling capabilities.

## Features

- Send basic HTML or plain text emails with ease
- Use pre-defined templates with dynamic data
- Send up to 500 personalized emails in bulk
- Schedule emails for future delivery
- Manage scheduled emails (list & delete)
- Add tags, custom headers, and reference IDs
- Attach files to your emails
- Support for multiple recipients, CC, BCC, and Reply-To
- Enable or disable open and click tracking
- Built-in input validation and error handling

## Requirements

- Python 3.8 or higher
- `requests` package
- (Optional) `python-magic` for advanced MIME type detection

## Installation

Install via pip:

```bash
pip install maileroo
```

## Quick Start

```python
from maileroo import MailerooClient, EmailAddress

# Initialize the client
client = MailerooClient("your-api-key")

# Send a basic email
reference_id = client.send_basic_email({
    "from": EmailAddress("sender@example.com", "Sender Name"),
    "to": [EmailAddress("recipient@example.com", "Recipient Name")],
    "subject": "Hello from Maileroo!",
    "html": "<h1>Hello World!</h1><p>This is a test email.</p>",
    "plain": "Hello World! This is a test email."
})

print("Email sent with reference ID:", reference_id)
```

---

## Usage Examples

### 1. Basic Email with Attachments

```python
from maileroo import MailerooClient, EmailAddress, Attachment

client = MailerooClient("your-api-key")

att1 = Attachment.from_file("report.pdf", content_type="application/pdf")
att2 = Attachment.from_content("data.csv", b"Name,Email\nJohn,john@example.com", content_type="text/csv")

reference_id = client.send_basic_email({
    "from": EmailAddress("sender@example.com", "Your Company"),
    "to": [
        EmailAddress("john@example.com", "John Doe"),
        EmailAddress("jane@example.com")
    ],
    "cc": [EmailAddress("manager@example.com", "Manager")],
    "bcc": [EmailAddress("archive@example.com")],
    "reply_to": EmailAddress("support@example.com", "Support Team"),
    "subject": "Monthly Report",
    "html": "<h1>Monthly Report</h1><p>Please find the report attached.</p>",
    "plain": "Monthly Report - Please find the report attached.",
    "attachments": [att1, att2],
    "tracking": True,
    "tags": {"campaign": "monthly-report", "type": "business"},
    "headers": {"X-Custom-Header": "Custom Value"}
})
```

---

### 2. Template Email

```python
from maileroo import MailerooClient, EmailAddress

client = MailerooClient("your-api-key")

reference_id = client.send_templated_email({
    "from": EmailAddress("noreply@example.com", "Your App"),
    "to": EmailAddress("user@example.com", "John Doe"),
    "subject": "Welcome to Our Service!",
    "template_id": 123,
    "template_data": {
        "user_name": "John Doe",
        "activation_link": "https://example.com/activate/abc123",
        "company_name": "Your Company"
    }
})
```

---

### 3. Bulk Email Sending (With Plain and HTML)

```python
from maileroo import MailerooClient, EmailAddress

client = MailerooClient("your-api-key")

result = client.send_bulk_emails({
    "subject": "Newsletter - March 2024",
    "html": "<h1>Hello {{name}}!</h1><p>Here is your personalized newsletter.</p>",
    "plain": "Hello {{name}}! Here is your personalized newsletter.",
    "tracking": False,
    "tags": {"campaign": "newsletter", "month": "march"},
    "messages": [
        {
            "from": EmailAddress("newsletter@example.com", "Newsletter Team"),
            "to": EmailAddress("john@example.com", "John Doe"),
            "cc": [EmailAddress("manager@example.com", "Manager")],
            "bcc": [EmailAddress("archive@example.com")],
            "reply_to": EmailAddress("support@example.com", "Support"),
            "template_data": {"name": "John"},
            "reference_id": "custom-ref-001"
        },
        {
            "from": EmailAddress("newsletter@example.com", "Newsletter Team"),
            "to": EmailAddress("jane@example.com", "Jane Smith"),
            "template_data": {"name": "Jane"}
        }
    ]
})

for ref_id in result:
    print("Email sent with reference ID:", ref_id)
```

---

### 4. Bulk Email Sending (With Template ID)

```python
from maileroo import MailerooClient, EmailAddress, Attachment

client = MailerooClient("your-api-key")

guide = Attachment.from_file("welcome-guide.pdf")

result = client.send_bulk_emails({
    "subject": "Welcome to Our Service!",
    "template_id": 123,
    "tracking": True,
    "tags": {"campaign": "welcome", "type": "onboarding"},
    "messages": [
        {
            "from": EmailAddress("welcome@example.com", "Welcome Team"),
            "to": EmailAddress("newuser1@example.com", "New User 1"),
            "template_data": {
                "user_name": "New User 1",
                "activation_link": "https://example.com/activate/token1",
                "company_name": "Your Company"
            }
        },
        {
            "from": EmailAddress("welcome@example.com", "Welcome Team"),
            "to": EmailAddress("newuser2@example.com", "New User 2"),
            "template_data": {
                "user_name": "New User 2",
                "activation_link": "https://example.com/activate/token2",
                "company_name": "Your Company"
            }
        }
    ],
    "attachments": [guide]
})

for ref_id in result:
    print("Email sent with reference ID:", ref_id)
```

---

### 5. Working with Attachments

```python
import io
from maileroo import Attachment

# From file
att1 = Attachment.from_file("document.pdf", content_type="application/pdf")

# From string content
att2 = Attachment.from_content("contacts.csv", b"Name,Email\nJohn,john@example.com", content_type="text/csv")

# From base64 content
att3 = Attachment.from_content("hello.txt", "SGVsbG8h", content_type="text/plain", is_base64=True)

# From stream
with open("file.txt", "rb") as f:
    att4 = Attachment.from_stream("file.txt", f, content_type="text/plain")

# Inline attachment (for embedding in HTML)
inline_image = Attachment.from_file("logo.png", content_type="image/png", inline=True)
```

---

### 6. Scheduling Emails

```python
from datetime import datetime, timedelta, timezone
from maileroo import MailerooClient, EmailAddress

client = MailerooClient("your-api-key")

scheduled_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

ref_id = client.send_basic_email({
    "from": EmailAddress("scheduler@example.com", "Scheduler"),
    "to": EmailAddress("recipient@example.com", "Recipient"),
    "subject": "Scheduled Email - Daily Report",
    "html": "<h1>Daily Report</h1><p>This was scheduled for delivery.</p>",
    "plain": "Daily Report - scheduled for delivery.",
    "scheduled_at": scheduled_time
})

print("Email scheduled with reference ID:", ref_id)
```

---

### 7. Managing Scheduled Emails

```python
from maileroo import MailerooClient

client = MailerooClient("your-api-key")

response = client.get_scheduled_emails(page=1, per_page=20)

print("Page:", response["page"], "/", response["total_pages"])
print("Total emails:", response["total_count"])

for email in response["results"]:
    print("ID:", email["reference_id"])
    print("From:", email["from"])
    print("Subject:", email["subject"])
    print("Scheduled:", email["scheduled_at"])
    print("Recipients:", ", ".join(email["recipients"]))

    if email.get("tags"):
        print("Tags:", email["tags"])
    if email.get("headers"):
        print("Headers:", email["headers"])

    # Cancel if needed
    if email["reference_id"] == "some-ref-id":
        client.delete_scheduled_email(email["reference_id"])
        print("Email cancelled")
```

---

### 8. Deleting Scheduled Email

```python
from maileroo import MailerooClient

client = MailerooClient("your-api-key")

try:
    client.delete_scheduled_email("your-reference-id")
    print("Scheduled email cancelled successfully.")
except Exception as e:
    print("Error cancelling scheduled email:", e)
```

---

## API Reference

### MailerooClient

```
MailerooClient(api_key: str, timeout: int = 30)
```

#### Methods

- `send_basic_email(data: dict) -> str`
- `send_templated_email(data: dict) -> str`
- `send_bulk_emails(data: dict) -> List[str]`
- `delete_scheduled_email(reference_id: str) -> bool`
- `get_scheduled_emails(page: int = 1, per_page: int = 10) -> dict`
- `get_reference_id() -> str`

---

### EmailAddress

```
EmailAddress(address: str, display_name: Optional[str] = None)
```

- `.to_dict() -> dict`

---

### Attachment

Static factory methods:

- `Attachment.from_file(path: str, content_type: Optional[str] = None, inline: bool = False)`
- `Attachment.from_content(file_name: str, content: Union[str, bytes], content_type: Optional[str] = None, inline: bool = False, is_base64: bool = False)`
- `Attachment.from_stream(file_name: str, stream, content_type: Optional[str] = None, inline: bool = False)`

---

## Error Handling

The SDK raises `ValueError` for input validation errors and `RuntimeError` for API failures:

```
from maileroo import MailerooClient

try:
    client = MailerooClient("your-api-key")
    ref_id = client.send_basic_email(email_data)
    print("Email sent:", ref_id)
except Exception as e:
    print("Unexpected error:", e)
```

---

## Documentation

For detailed API documentation, including all endpoints and parameters, see the [Maileroo API Docs](https://maileroo.com/docs).

## License

This SDK is released under the MIT License.

## Support

Please visit our [support page](https://maileroo.com/contact-form) for assistance. If you find bugs or have feature requests, open an issue on our GitHub repository.