from django.contrib import admin
from django.utils.html import format_html
from .models import Team, Match, Bet, HouseFee, BetClaim
from decimal import Decimal

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'logo_display', 'created_at']
    search_fields = ['name']
    list_filter = ['created_at']
    
    def logo_display(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />', obj.logo.url)
        return "No Logo"
    logo_display.short_description = 'Logo'

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['team_a', 'team_b', 'start_time', 'result', 'total_bets', 'total_pool', 'is_active']
    list_filter = ['result', 'is_active', 'start_time', 'created_at']
    search_fields = ['team_a__name', 'team_b__name']
    date_hierarchy = 'start_time'
    actions = ['set_result_a', 'set_result_b', 'set_result_draw', 'activate_matches', 'deactivate_matches']
    
    def activate_matches(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"Activated {queryset.count()} match(es) for betting")
    activate_matches.short_description = "Activate matches for betting"
    
    def deactivate_matches(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {queryset.count()} match(es) from betting")
    deactivate_matches.short_description = "Deactivate matches from betting"
    def set_result_a(self, request, queryset):
        print('ADMIN ACTION TRIGGRED: set_result_home')
        for match in queryset:
            match.result = 'A'
            match.save()
            # Update all bets for this match
            self.update_bets_for_match(match)
        self.message_user(request, f"Set {queryset.count()} match(es) result to Team A Wins")
    set_result_a.short_description = "Set result: Team A Wins"
    
    def set_result_b(self, request, queryset):
        print('ADMIN ACTION TRIGGRED: set_result_away')
        for match in queryset:
            match.result = 'B'
            match.save()
            # Update all bets for this match
            self.update_bets_for_match(match)
        self.message_user(request, f"Set {queryset.count()} match(es) result to Team B Wins")
    set_result_b.short_description = "Set result: Team B Wins"
    def set_result_draw(self, request, queryset):
        print('ADMIN ACTION TRIGGRED: set_result_draw')
        for match in queryset:
            match.result = 'D'
            match.save()
            # Update all bets for this match
            self.update_bets_for_match(match)
        self.message_user(request, f"Set {queryset.count()} match(es) result to Draw")
    set_result_draw.short_description = "Set result: Draw"
    print(f"starting update bets for match")
    def update_bets_for_match(self, match):
        """Update all bets for a match when result is set"""
        if not match.house_fee_recorded:
            loser_pool = match.loser_pool
            house_fee =  loser_pool * Decimal('0.10') if loser_pool > 0  else Decimal('0.00')

            match.house_fee = house_fee
            match.house_fee_recorded = True
            match.save()
            
            HouseFee.objects.create(match=match, amount=house_fee)
        # Mark winners and calculate payouts
        for bet in match.bet_set.all():
            #print(f"Updating Bet {bet.bet_code}: bet_choice={bet.bet_choice!r}, match.result={match.result!r}")
            is_winner = (bet.bet_choice == match.result)
            #print(f"the winner of the matchup is {is_winner}")
            bet.is_winner = is_winner
            if is_winner:
                bet.payout = bet.calculate_payout()
            else:
                bet.payout = 0
            bet.save()

@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = ['bettor_name', 'bettor_email', 'match', 'bet_choice', 'amount', 'bet_code', 'payout', 'is_winner', 'is_paid_out', 'created_at']
    list_filter = [ 'bet_choice', 'created_at', 'match','is_winner', 'is_paid_out']
    search_fields = ['bettor_name', 'bettor_email', 'bet_code', 'paystack_reference']
    readonly_fields = ['bet_code', 'payout', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    actions = ['mark_as_paid_out', 'mark_as_not_paid_out']
    
    def mark_as_paid_out(self, request, queryset):
        queryset.update(is_paid_out=True)
        self.message_user(request, f"Marked {queryset.count()} bet(s) as paid out")
    mark_as_paid_out.short_description = "Mark as paid out"
    
    def mark_as_not_paid_out(self, request, queryset):
        queryset.update(is_paid_out=False)
        self.message_user(request, f"Marked {queryset.count()} bet(s) as not paid out")
    mark_as_not_paid_out.short_description = "Mark as not paid out"

@admin.register(HouseFee)
class HouseFeeAdmin(admin.ModelAdmin):
    list_display = ['match', 'amount', 'created_at','updated_at']
    list_filter = ['created_at']
    search_fields = ['match__team_a__name', 'match__team_b__name']

@admin.register(BetClaim)
class BetClaimAdmin(admin.ModelAdmin):
    list_display = ('bet', 'account_name', 'account_number', 'bank_name', 'payout_amount', 'processed', 'created_at')
    search_fields = ('account_name', 'account_number', 'bank_name', 'bet__bet_code')
    list_filter = ('bank_name', 'processed', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('bet', 'account_name', 'account_number', 'bank_name', 'bank_code', 'payout_amount', 'claimed_at', 'created_at')
    actions = ['mark_as_processed', 'mark_as_not_processed']
    
    def mark_as_processed(self, request, queryset):
        for claim in queryset:
            claim.processed = True
            claim.save()  # This will trigger the save method that updates bet.is_paid_out
        self.message_user(request, f"Marked {queryset.count()} claim(s) as processed")
    mark_as_processed.short_description = "Mark as processed"
    
    def mark_as_not_processed(self, request, queryset):
        for claim in queryset:
            claim.processed = False
            claim.save()
        self.message_user(request, f"Marked {queryset.count()} claim(s) as not processed")
    mark_as_not_processed.short_description = "Mark as not processed"