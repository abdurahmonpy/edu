"""
Milestone 1 Adversarial Test Suite
Conducted by Challenger 2.

Comprehensive adversarial challenge testing covering:
1. Concurrency & Race Conditions during registration
2. Uzbek phone normalization, edge case casing/spacing, fuzzing & prefix validation
3. Password hashing security, storage verification, edge-case password inputs
4. Session handling, session rotation (fixation prevention), cookie security, user inactivation
5. Login redirect security (Open Redirect attacks, next parameter sanitization)
6. Template rendering & zero English hardcoded text in user-facing views
7. Model integrity & superuser-only admin privilege escalation attempts
"""
import re
import threading
from datetime import date
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
from django.utils.html import escape

from apps.accounts.utils import normalize_uzbek_phone, format_uzbek_phone_display, UZBEK_PHONE_REGEX
from apps.accounts.models import Student
from apps.accounts.forms import UserRegistrationForm, UserLoginForm
from apps.programs.models import Program

User = get_user_model()


class AdversarialRegistrationConcurrencyTest(TestCase):
    """
    Stress-testing concurrent registrations with identical phone numbers and duplicate handling.
    """
    def test_concurrent_user_registration_race_condition(self):
        """
        Simulate concurrent registration requests attempting to register the exact same phone number.
        Checks if the database unique constraint prevents duplicate records and handles exceptions.
        """
        phone = "901234500"
        results = []
        errors = []

        def register_user(worker_id):
            try:
                # Direct model creation race test
                u = User.objects.create_user(
                    phone_number=phone,
                    password="password123",
                    first_name=f"User_{worker_id}"
                )
                results.append(u)
            except IntegrityError as e:
                errors.append(e)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_user, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly 1 user must succeed, the rest must fail with IntegrityError
        self.assertEqual(len(results), 1, f"Expected exactly 1 user created, got {len(results)}")
        self.assertEqual(User.objects.filter(phone_number="+998901234500").count(), 1)
        # Ensure only 1 Student profile was created
        self.assertEqual(Student.objects.filter(user__phone_number="+998901234500").count(), 1)

    def test_duplicate_registration_various_formats(self):
        """
        Register a user with one format (+998901112233) and attempt registration with
        alternate representations (e.g. '901112233', '8 90 111 22 33', '+998 (90) 111-22-33').
        """
        User.objects.create_user(
            phone_number="+998901112233",
            password="testpassword123",
            first_name="Original"
        )

        variants = [
            "901112233",
            "998901112233",
            "+998 90 111 22 33",
            "+998 (90) 111-22-33",
            "8 90 111 22 33",
            "8901112233",
            "90-111-22-33",
            "   +998 90 111 22 33   ",
        ]

        for variant in variants:
            with self.subTest(variant=variant):
                form = UserRegistrationForm(data={
                    'first_name': 'DuplicateAttempt',
                    'phone_number': variant,
                    'password': 'password123',
                    'password_confirm': 'password123'
                })
                self.assertFalse(form.is_valid(), f"Form should be invalid for variant {variant}")
                self.assertIn('phone_number', form.errors)
                self.assertEqual(
                    form.errors['phone_number'],
                    ["Ushbu telefon raqami allaqachon ro'yxatdan o'tgan."]
                )


class AdversarialPhoneValidationAndFuzzingTest(TestCase):
    """
    Stress-testing phone normalization against boundary conditions, injection, fuzzing, and prefix validation.
    """
    def test_unsupported_and_fuzzed_phone_inputs(self):
        fuzzed_inputs = [
            # SQL injection attempt in phone
            "901234567' OR '1'='1",
            # XSS attempt in phone
            "<script>alert(1)</script>",
            # Extreme lengths
            "90" + "1" * 100,
            "1",
            "",
            None,
            "     ",
            "\t\n+998901234567\n",
            # Non-Uzbek country codes
            "+12025550123",
            "+79991234567",
            "+447911123456",
            # Letters inside
            "+99890123456A",
            "+998(90)123-45-6a",
            # Truncated or overly long
            "+99890123456",     # 8 digits
            "+9989012345678",   # 10 digits
            "90123456",         # 8 digits
            "9012345678",       # 10 digits
        ]
        for inp in fuzzed_inputs:
            with self.subTest(inp=inp):
                if inp is None or not str(inp).strip():
                    with self.assertRaises(ValidationError):
                        normalize_uzbek_phone(inp)
                else:
                    digits = re.sub(r'[^\d+]', '', str(inp)).lstrip('+')
                    if len(digits) not in (9, 10, 12) or (len(digits) == 10 and not digits.startswith('8')) or (len(digits) == 12 and not digits.startswith('998')) or not digits.isdigit():
                        with self.assertRaises(ValidationError):
                            normalize_uzbek_phone(inp)

    def test_uzbek_operator_prefix_check(self):
        """
        Investigate whether normalize_uzbek_phone validates real Uzbek telecom operator prefixes
        (33, 50, 55, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 88, 90, 91, 93, 94, 95, 97, 98, 99).
        Notice: UZBEK_PHONE_REGEX regex is defined in utils.py.
        """
        valid_prefix_number = "+998901234567"
        self.assertTrue(bool(UZBEK_PHONE_REGEX.match(valid_prefix_number)))

        invalid_prefix_number = "+998121234567"  # 12 is not an assigned Uzbek mobile/landline prefix
        # Check that UZBEK_PHONE_REGEX correctly flags invalid operator prefix
        self.assertFalse(bool(UZBEK_PHONE_REGEX.match(invalid_prefix_number)))


class AdversarialPasswordSecurityTest(TestCase):
    """
    Stress-testing password hashing algorithm, password complexity, and edge cases.
    """
    def test_password_is_properly_hashed_and_not_stored_plaintext(self):
        """Verify password is never stored in plain text and uses strong PBKDF2/Argon2 hasher."""
        raw_pass = "My$ecureP@ssw0rd!2026"
        user = User.objects.create_user(
            phone_number="909876543",
            password=raw_pass,
            first_name="Nodir"
        )
        # Password must not be plaintext
        self.assertNotEqual(user.password, raw_pass)
        self.assertNotIn(raw_pass, user.password)
        # Hasher must be a secure registered Django hasher
        hasher = identify_hasher(user.password)
        self.assertTrue(hasher.algorithm.startswith(('pbkdf2', 'argon2', 'bcrypt')), f"Hasher was {hasher.algorithm}")
        self.assertTrue(user.check_password(raw_pass))
        self.assertFalse(user.check_password("WrongPassword"))

    def test_password_whitespace_and_empty_edge_cases(self):
        """Test passwords containing whitespace strings."""
        form = UserRegistrationForm(data={
            'first_name': 'Test',
            'phone_number': '901234567',
            'password': '      ',  # 6 spaces
            'password_confirm': '      '
        })
        # Cleaned password handling: CharField strips whitespace to empty string
        # Resulting in required password validation triggering or length error
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

    def test_password_short_length_rejection(self):
        """Passwords < 6 chars must be rejected."""
        for short_pass in ["1", "12", "123", "1234", "12345"]:
            with self.subTest(short_pass=short_pass):
                form = UserRegistrationForm(data={
                    'first_name': 'Short',
                    'phone_number': '901234567',
                    'password': short_pass,
                    'password_confirm': short_pass
                })
                self.assertFalse(form.is_valid())
                self.assertIn('password', form.errors)


class AdversarialSessionAndAuthSecurityTest(TestCase):
    """
    Stress-testing session handling, session rotation on login, fixation resistance,
    and access state transitions.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number="901239999",
            password="validpassword123",
            first_name="Sardor"
        )

    def test_session_fixation_protection_and_key_rotation(self):
        """
        Verify that upon successful login, the session key is rotated (cycled)
        to prevent session fixation attacks.
        """
        # Create an anonymous session first
        self.client.get(reverse('accounts:login'))
        anonymous_session_key = self.client.session.session_key
        
        # Log in
        response = self.client.post(reverse('accounts:login'), {
            'phone_number': '901239999',
            'password': 'validpassword123'
        })
        self.assertEqual(response.status_code, 302)
        
        authenticated_session_key = self.client.session.session_key
        self.assertIsNotNone(authenticated_session_key)
        self.assertNotEqual(
            anonymous_session_key, 
            authenticated_session_key,
            "Session key must be rotated after authentication to prevent session fixation."
        )

    def test_inactive_user_cannot_login(self):
        """Verify inactive users (is_active=False) cannot log in."""
        self.user.is_active = False
        self.user.save()

        response = self.client.post(reverse('accounts:login'), {
            'phone_number': '901239999',
            'password': 'validpassword123'
        })
        self.assertEqual(response.status_code, 200)
        # Inactive user is rejected by PhoneAuthBackend and shown login error
        self.assertContains(response, "Telefon raqami yoki parol noto&#x27;g&#x27;ri.")

    def test_active_session_with_inactivated_user(self):
        """
        If a user is logged in and subsequently set to is_active=False in the database,
        subsequent requests must not recognize them as active authenticated users.
        """
        self.client.login(username='+998901239999', password='validpassword123')
        # Inactivate user
        self.user.is_active = False
        self.user.save()

        # Make request to login view (should NOT redirect as authenticated user)
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_logout_invalidates_session(self):
        """Verify logout flushes session and clears auth cookie."""
        self.client.login(username='+998901239999', password='validpassword123')
        session_key_before = self.client.session.session_key

        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))
        
        # Check session key after logout
        session_key_after = self.client.session.session_key
        self.assertNotEqual(session_key_before, session_key_after)


class AdversarialLoginRedirectSecurityTest(TestCase):
    """
    Stress-testing login redirection against Open Redirect vulnerabilities and phishing bypasses.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="907771122",
            password="securepassword123",
            first_name="Gulnoza"
        )
        self.user.student_profile.onboarding_completed = True
        self.user.student_profile.save()

    def test_open_redirect_attacks_are_blocked(self):
        """
        Adversarially test malicious next parameters to ensure no external redirects occur.
        """
        malicious_urls = [
            "https://evil.com",
            "http://attacker.com/steal_cookies",
            "//evil.com",
            "//evil.com/phishing",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "\\\\evil.com",
            "https://evil.com?param=http://testserver",
            "ftp://evil.com",
        ]

        for evil_url in malicious_urls:
            with self.subTest(evil_url=evil_url):
                client = Client()
                response = client.post(f"{reverse('accounts:login')}?next={evil_url}", {
                    'phone_number': '907771122',
                    'password': 'securepassword123'
                })
                # Must redirect to default dashboard:index, NEVER to evil_url
                self.assertEqual(response.status_code, 302)
                self.assertNotEqual(response.url, evil_url)
                self.assertEqual(response.url, reverse('dashboard:index'))

    def test_valid_internal_redirects_are_allowed(self):
        """Legitimate local URLs should be followed."""
        valid_urls = [
            reverse('programs:catalog'),
            reverse('tasks:list'),
            reverse('mentor:chat'),
            reverse('dashboard:index'),
        ]
        for valid_url in valid_urls:
            with self.subTest(valid_url=valid_url):
                client = Client()
                response = client.post(f"{reverse('accounts:login')}?next={valid_url}", {
                    'phone_number': '907771122',
                    'password': 'securepassword123'
                })
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, valid_url)


class AdversarialZeroEnglishI18nTest(TestCase):
    """
    Stress-testing template rendering and verifying zero English hardcoded text in user-facing views.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number="905554433",
            password="testpassword123",
            first_name="Zilola"
        )

    def test_login_and_register_pages_contain_no_raw_english_labels(self):
        """
        Check registration and login rendered HTML for forbidden English UI strings.
        """
        forbidden_english_words = [
            r'\bSign In\b', r'\bSign Up\b', r'\bRegister\b(?!.*accounts/register)', 
            r'\bLogin\b(?!.*accounts/login)', r'\bFirst Name\b', r'\bPassword Confirmation\b',
            r'\bRemember Me\b', r'\bForgot Password\b', r'\bSubmit\b',
            r'\bDashboard\b(?!.*dashboard)', r'\bHome\b', r'\bWelcome\b',
            r'\bTasks\b(?!.*tasks)', r'\bPrograms\b(?!.*programs)', r'\bLogout\b(?!.*accounts/logout)'
        ]

        pages_to_check = [
            reverse('accounts:login'),
            reverse('accounts:register'),
        ]

        for page in pages_to_check:
            response = self.client.get(page)
            content = response.content.decode('utf-8')
            for forbidden_regex in forbidden_english_words:
                match = re.search(forbidden_regex, content, re.IGNORECASE)
                if match:
                    matched_text = match.group(0)
                    visible_text_search = re.findall(rf'>\s*[^<]*{re.escape(matched_text)}[^<]*<', content, re.IGNORECASE)
                    self.assertEqual(
                        len(visible_text_search), 0,
                        f"Found user-visible English text '{matched_text}' in {page}: {visible_text_search}"
                    )

    def test_disclaimer_is_rendered_and_matches_exact_uzbek_specification(self):
        """
        Verify exact disclaimer string:
        'AI tavsiyasi — yakuniy qarorni oila va o\'quvchi qabul qiladi.'
        """
        expected_disclaimer = "AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
        response = self.client.get(reverse('accounts:login'))
        self.assertContains(response, escape(expected_disclaimer))
