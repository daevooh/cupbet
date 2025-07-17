from django.db import models
from django.utils import timezone
from decimal import Decimal
import uuid
import random
import string

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='team_logos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Match(models.Model):
    RESULT_CHOICES = [
        ('A', 'Team A Wins'),
        ('B', 'Team B Wins'),
        ('D', 'Draw'),
        ('P', 'Pending'),  # Match hasn't been played yet
    ]
    
    team_a = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    team_b = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    start_time = models.DateTimeField()
    result = models.CharField(max_length=1, choices=RESULT_CHOICES, default='P')
    is_active = models.BooleanField(default=True)  # For admin to disable betting
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    house_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    house_fee_recorded = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.team_a} vs {self.team_b} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def total_bets(self):
        return self.bet_set.count()
    
    @property
    def total_pool(self):
        return self.bet_set.aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def winner_pool(self):
        if self.result == 'P':
            return 0
        winning_bets = self.bet_set.filter(bet_choice=self.result)
        return winning_bets.aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def loser_pool(self):
        if self.result == 'P':
            return 0
        losing_bets = self.bet_set.exclude(bet_choice=self.result)
        return losing_bets.aggregate(total=models.Sum('amount'))['total'] or 0
    
    class Meta:
        ordering = ['-start_time']
class HouseFee(models.Model):
    match = models.OneToOneField('Match', on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    #total_house_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.match} - ₦{self.amount}" if self.match else f"House Fee: ₦{self.amount}"
class Bet(models.Model):
    BET_CHOICES = [
        ('A', 'Team A Wins'),
        ('B', 'Team B Wins'),
        ('D', 'Draw'),
    ]
    
    bettor_name = models.CharField(max_length=100)
    bettor_email = models.EmailField(max_length=254, blank=True, null=True)  # Make optional for existing records
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    bet_choice = models.CharField(max_length=1, choices=BET_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bet_code = models.CharField(max_length=20, unique=True, blank=True)
    payout = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_winner = models.BooleanField(default=False)
    is_paid_out = models.BooleanField(default=False)
    paystack_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.bettor_name} - {self.bet_code} - {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.bet_code:
            self.bet_code = self.generate_bet_code()
        super().save(*args, **kwargs)
    
    def generate_bet_code(self):
        """Generate a unique bet code like BET-8321X"""
        while True:
            # Generate 4 random digits
            digits = ''.join(random.choices(string.digits, k=4))
            # Generate 1 random uppercase letter
            letter = random.choice(string.ascii_uppercase)
            bet_code = f"BET-{digits}{letter}"
            
            # Check if this code already exists
            if not Bet.objects.filter(bet_code=bet_code).exists():
                return bet_code
    
    def calculate_payout(self):
        """Calculate payout based on peer-pool system"""
        if self.match.result == 'P' or not self.is_winner:
            return Decimal('0.00')
        
        # Get total loser pool for this match
        total_pool = self.match.total_pool
        loser_pool =  self.match.loser_pool
        winner_pool = self.match.winner_pool
       
        
        if loser_pool == 0:
            return round(self.amount, 2)
    
        
        
        # everyone won - return stake, no house fee taken
        house_fee = total_pool * Decimal('0.10')
        if not self.match.house_fee_recorded:
            self.match.house_fee = house_fee
            self.match.house_fee_recorded = True
            self.match.save()

            try:
                pool = HouseFee.object.first()
                if not pool:
                    pool = HouseFee.objects.create()
                pool.update_housse_fee(house_fee)
            except:
                pass
        distributable_pool = loser_pool - house_fee

        # avoid division by zero
        if winner_pool == 0 or distributable_pool <= 0:
            return round(self.amount, 2)


        payout = self.amount + (self.amount / winner_pool) * distributable_pool   
        return round(payout, 2)
    
    class Meta:
        ordering = ['-created_at']
class BetClaim(models.Model):
    bet = models.OneToOneField(Bet, on_delete=models.CASCADE, related_name='claim')  # one claim per bet
    account_number = models.CharField(max_length=20)
    account_name = models.CharField(max_length=100, blank=True, null=True)  # optional, for display
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=20)
    payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Store the payout amount
    claimed_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)  # for admin manual payout
    created_at = models.DateTimeField(default=timezone.now)
    
    def save(self, *args, **kwargs):
        # Auto-set payout amount from bet if not set
        if not self.payout_amount and self.bet:
            self.payout_amount = self.bet.payout
        super().save(*args, **kwargs)
        
        # Update bet's is_paid_out status when processed
        if self.processed and self.bet and not self.bet.is_paid_out:
            self.bet.is_paid_out = True
            self.bet.save()
    
    def __str__(self):
        return f"{self.bet.bet_code} - ₦{self.payout_amount} - {self.account_name}"