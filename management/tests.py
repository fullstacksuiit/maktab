from datetime import date
from decimal import Decimal

from django.test import TestCase

from management.models import Organization, Course, Batch, Student, FeePayment


class FeeTestBase(TestCase):
    """Shared setup for fee-related tests."""

    def setUp(self):
        self.org = Organization.objects.create(
            org_name='Test Maktab',
            address='123 Test St',
            contact='1234567890',
        )
        self.course = Course.objects.create(
            course_name='Quran Recitation',
            course_code='QR001',
            fees=Decimal('500.00'),
            fee_period='monthly',
            organization=self.org,
        )
        self.batch = Batch.objects.create(
            batch_code='BTH001',
            batch_name='Morning Batch',
            course=self.course,
            organization=self.org,
        )

    def _create_student(self, **kwargs):
        defaults = {
            'full_name': 'Test Student',
            'phone': '9876543210',
            'gender': 'M',
            'address': '456 Student Lane',
            'enrollment_date': date.today(),
            'organization': self.org,
        }
        defaults.update(kwargs)
        student = Student.objects.create(**defaults)
        student.batches.add(self.batch)
        return student


class EffectiveFeeTests(FeeTestBase):
    """Tests for Student.get_effective_fee()."""

    def test_no_discount(self):
        student = self._create_student()
        self.assertEqual(student.get_effective_fee(), Decimal('500.00'))

    def test_fixed_discount(self):
        student = self._create_student(discount_type='fixed', discount_value=Decimal('200.00'))
        self.assertEqual(student.get_effective_fee(), Decimal('300.00'))

    def test_percentage_discount(self):
        student = self._create_student(discount_type='percentage', discount_value=Decimal('10'))
        self.assertEqual(student.get_effective_fee(), Decimal('450.00'))

    def test_orphan_waiver(self):
        student = self._create_student(is_orphan=True)
        self.assertEqual(student.get_effective_fee(), 0)

    def test_orphan_overrides_discount(self):
        """Orphan status should take priority over any discount."""
        student = self._create_student(
            is_orphan=True,
            discount_type='fixed',
            discount_value=Decimal('200.00'),
        )
        self.assertEqual(student.get_effective_fee(), 0)

    def test_fixed_discount_cannot_go_negative(self):
        student = self._create_student(discount_type='fixed', discount_value=Decimal('999.00'))
        self.assertEqual(student.get_effective_fee(), Decimal('0'))

    def test_percentage_discount_100_percent(self):
        student = self._create_student(discount_type='percentage', discount_value=Decimal('100'))
        self.assertEqual(student.get_effective_fee(), Decimal('0.00'))

    def test_zero_discount_value_means_no_discount(self):
        student = self._create_student(discount_type='fixed', discount_value=Decimal('0'))
        self.assertEqual(student.get_effective_fee(), Decimal('500.00'))

    def test_multiple_batches_fees_sum(self):
        """Effective fee should sum fees from all enrolled batches."""
        course2 = Course.objects.create(
            course_name='Arabic Grammar',
            course_code='AG001',
            fees=Decimal('300.00'),
            fee_period='monthly',
            organization=self.org,
        )
        batch2 = Batch.objects.create(
            batch_code='BTH002',
            batch_name='Evening Batch',
            course=course2,
            organization=self.org,
        )
        student = self._create_student()
        student.batches.add(batch2)
        # 500 + 300 = 800
        self.assertEqual(student.get_effective_fee(), Decimal('800.00'))

    def test_fixed_discount_on_multiple_batches(self):
        course2 = Course.objects.create(
            course_name='Arabic Grammar',
            course_code='AG001',
            fees=Decimal('300.00'),
            fee_period='monthly',
            organization=self.org,
        )
        batch2 = Batch.objects.create(
            batch_code='BTH002',
            batch_name='Evening Batch',
            course=course2,
            organization=self.org,
        )
        student = self._create_student(discount_type='fixed', discount_value=Decimal('200.00'))
        student.batches.add(batch2)
        # (500 + 300) - 200 = 600
        self.assertEqual(student.get_effective_fee(), Decimal('600.00'))

    def test_no_batches_enrolled(self):
        student = self._create_student()
        student.batches.clear()
        self.assertEqual(student.get_effective_fee(), Decimal('0'))


class PendingFeeTests(FeeTestBase):
    """Tests for Student.get_pending_fees()."""

    def test_no_payments(self):
        student = self._create_student()
        self.assertEqual(student.get_pending_fees(), Decimal('500.00'))

    def test_partial_payment(self):
        student = self._create_student()
        FeePayment.objects.create(
            student=student,
            batch=self.batch,
            amount=Decimal('200.00'),
            payment_date=date.today(),
            payment_method='Cash',
            status='Approved',
            organization=self.org,
        )
        self.assertEqual(student.get_pending_fees(), Decimal('300.00'))

    def test_only_approved_payments_count(self):
        student = self._create_student()
        FeePayment.objects.create(
            student=student,
            batch=self.batch,
            amount=Decimal('500.00'),
            payment_date=date.today(),
            payment_method='UPI',
            status='Pending',
            organization=self.org,
        )
        # Pending payment shouldn't reduce balance
        self.assertEqual(student.get_pending_fees(), Decimal('500.00'))

    def test_rejected_payments_dont_count(self):
        student = self._create_student()
        FeePayment.objects.create(
            student=student,
            batch=self.batch,
            amount=Decimal('500.00'),
            payment_date=date.today(),
            payment_method='Cash',
            status='Rejected',
            organization=self.org,
        )
        self.assertEqual(student.get_pending_fees(), Decimal('500.00'))

    def test_opening_balance_added(self):
        student = self._create_student(opening_balance=Decimal('1000.00'))
        # 500 (fee) + 1000 (opening) - 0 (paid) = 1500
        self.assertEqual(student.get_pending_fees(), Decimal('1500.00'))

    def test_opening_balance_with_payment(self):
        student = self._create_student(opening_balance=Decimal('1000.00'))
        FeePayment.objects.create(
            student=student,
            batch=self.batch,
            amount=Decimal('700.00'),
            payment_date=date.today(),
            payment_method='Cash',
            status='Approved',
            organization=self.org,
        )
        # 500 + 1000 - 700 = 800
        self.assertEqual(student.get_pending_fees(), Decimal('800.00'))

    def test_orphan_with_opening_balance(self):
        student = self._create_student(is_orphan=True, opening_balance=Decimal('300.00'))
        # 0 (orphan fee) + 300 (opening) - 0 (paid) = 300
        self.assertEqual(student.get_pending_fees(), Decimal('300.00'))
