from datetime import datetime, timedelta
import math
from ..utils.db_connector import db_connector

class BillingService:
    """Core billing logic for parking fees calculation"""
    
    @staticmethod
    def calculate_parking_fee(record_id):
        """
        Calculate parking fee based on complex billing logic
        
        Logic:
        - Scenario A (First time): If PaidUntilTime is NULL, calculate from EntryTime
        - Scenario B (Subsequent): If PaidUntilTime is not NULL, calculate from PaidUntilTime
        - Free parking for first 15 minutes (Scenario A only)
        - After 15 min: CEILING(hours) * hourly_rate
        - Apply daily maximum cap if applicable
        """
        try:
            # Get parking record with lot information
            query = """
                SELECT pr.*, pl.HourlyRate, pl.DailyMaxRate, pl.Name as LotName
                FROM PARKING_RECORD pr
                JOIN PARKING_LOT pl ON pr.ParkingLotID = pl.ParkingLotID
                WHERE pr.RecordID = %s
            """
            result = db_connector.execute_query(query, (record_id,))
            
            if not result:
                raise ValueError("Parking record not found")
            
            record = result[0]
            current_time = datetime.now()
            
            # Determine calculation start time based on scenario
            if record['PaidUntilTime'] is None:
                # Scenario A: First payment
                calculation_start_time = record['EntryTime']
                apply_free_period = True
            else:
                # Scenario B: Subsequent payment
                calculation_start_time = record['PaidUntilTime']
                apply_free_period = False
            
            # Calculate parking duration in minutes
            duration_delta = current_time - calculation_start_time
            duration_minutes = duration_delta.total_seconds() / 60
            
            # Apply 15-minute free period for first-time payment only
            if apply_free_period and duration_minutes <= 15:
                return {
                    'fee': 0,
                    'duration_minutes': duration_minutes,
                    'duration_display': BillingService._format_duration(duration_minutes),
                    'calculation_start_time': calculation_start_time,
                    'current_time': current_time,
                    'scenario': 'A',
                    'record': record
                }
            
            # Calculate billable hours (ceiling)
            duration_hours = duration_minutes / 60
            billable_hours = math.ceil(duration_hours)
            
            # Calculate base fee
            base_fee = billable_hours * record['HourlyRate']
            
            # Apply daily maximum cap if set
            if record['DailyMaxRate'] and base_fee > record['DailyMaxRate']:
                # Calculate number of days (24-hour periods)
                duration_days = math.ceil(duration_hours / 24)
                final_fee = duration_days * record['DailyMaxRate']
            else:
                final_fee = base_fee
            
            return {
                'fee': final_fee,
                'base_fee': base_fee,
                'billable_hours': billable_hours,
                'duration_minutes': duration_minutes,
                'duration_display': BillingService._format_duration(duration_minutes),
                'calculation_start_time': calculation_start_time,
                'current_time': current_time,
                'scenario': 'A' if apply_free_period else 'B',
                'record': record,
                'capped': record['DailyMaxRate'] and base_fee > record['DailyMaxRate']
            }
            
        except Exception as e:
            raise Exception(f"Billing calculation error: {str(e)}")
    
    @staticmethod
    def _format_duration(minutes):
        """Format duration in minutes to human-readable string"""
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        
        if hours > 0:
            return f"{hours} 小時 {mins} 分鐘"
        else:
            return f"{mins} 分鐘"
    
    @staticmethod
    def apply_coupon_discount(record_id, coupon_codes):
        """
        Apply coupon discounts to parking fee
        Returns updated fee calculation with applied discounts
        """
        from .coupon_service import CouponService
        
        try:
            # Get current fee calculation
            fee_info = BillingService.calculate_parking_fee(record_id)
            original_fee = fee_info['fee']
            
            applied_coupons = []
            total_discount = 0
            
            for coupon_code in coupon_codes:
                # Validate coupon
                validation = CouponService.validate_coupon(coupon_code, record_id)
                
                if validation['valid']:
                    # Calculate discount (1 hour per coupon)
                    hourly_rate = fee_info['record']['HourlyRate']
                    discount_amount = min(hourly_rate, original_fee - total_discount)
                    
                    if discount_amount > 0:
                        applied_coupons.append({
                            'code': coupon_code,
                            'discount': discount_amount
                        })
                        total_discount += discount_amount
                else:
                    raise ValueError(f"Invalid coupon: {validation['reason']}")
            
            final_fee = max(0, original_fee - total_discount)
            
            return {
                **fee_info,
                'original_fee': original_fee,
                'total_discount': total_discount,
                'final_fee': final_fee,
                'applied_coupons': applied_coupons
            }
            
        except Exception as e:
            raise Exception(f"Coupon application error: {str(e)}")
    
    @staticmethod
    def process_payment(record_id, payment_amount, payment_method, applied_coupons=None):
        """
        Process payment and update records
        """
        try:
            # Get current fee calculation
            fee_info = BillingService.calculate_parking_fee(record_id)
            expected_amount = fee_info['fee']
            
            # Apply coupons if provided
            if applied_coupons:
                coupon_fee_info = BillingService.apply_coupon_discount(record_id, applied_coupons)
                expected_amount = coupon_fee_info['final_fee']
                
                # Mark coupons as used
                for coupon in applied_coupons:
                    CouponService.use_coupon(coupon, record_id)
            
            if payment_amount < expected_amount:
                raise ValueError(f"Insufficient payment. Expected: {expected_amount}, Received: {payment_amount}")
            
            current_time = datetime.now()
            exit_deadline = current_time + timedelta(minutes=15)
            
            # Update parking record
            update_query = """
                UPDATE PARKING_RECORD 
                SET PaidUntilTime = %s, TotalFee = %s
                WHERE RecordID = %s
            """
            db_connector.execute_query(update_query, (exit_deadline, expected_amount, record_id), fetch=False)
            
            # Insert payment record
            payment_query = """
                INSERT INTO PAYMENT_RECORD (RecordID, PaymentAmount, PaymentMethod, PaymentTime, TransactionID)
                VALUES (%s, %s, %s, %s, %s)
            """
            transaction_id = f"TXN{current_time.strftime('%Y%m%d%H%M%S')}{record_id}"
            db_connector.execute_query(payment_query, 
                                     (record_id, payment_amount, payment_method, current_time, transaction_id), 
                                     fetch=False)
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'exit_deadline': exit_deadline,
                'paid_amount': payment_amount,
                'change': payment_amount - expected_amount if payment_amount > expected_amount else 0
            }
            
        except Exception as e:
            raise Exception(f"Payment processing error: {str(e)}")

from .coupon_service import CouponService