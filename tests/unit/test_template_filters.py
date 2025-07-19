"""
Test cases for custom template filters
"""
from django.test import TestCase
from django.template import Context, Template


class MathFiltersTest(TestCase):
    """Test cases for math template filters"""
    
    def test_mul_filter(self):
        """Test multiplication filter"""
        template = Template("{% load math_filters %}{{ value|mul:multiplier }}")
        context = Context({'value': 10, 'multiplier': 5})
        result = template.render(context)
        self.assertEqual(result, '50.0')
    
    def test_div_filter(self):
        """Test division filter"""
        template = Template("{% load math_filters %}{{ value|div:divisor }}")
        context = Context({'value': 100, 'divisor': 4})
        result = template.render(context)
        self.assertEqual(result, '25.0')
    
    def test_div_by_zero(self):
        """Test division by zero returns 0"""
        template = Template("{% load math_filters %}{{ value|div:divisor }}")
        context = Context({'value': 100, 'divisor': 0})
        result = template.render(context)
        self.assertEqual(result, '0')
    
    def test_percentage_filter(self):
        """Test percentage calculation"""
        template = Template("{% load math_filters %}{{ value|percentage:total }}")
        context = Context({'value': 25, 'total': 100})
        result = template.render(context)
        self.assertEqual(result, '25.0')
    
    def test_complex_calculation(self):
        """Test complex calculation like in the financial template"""
        template = Template("{% load math_filters %}{{ net_profit|mul:100|div:total_bets|floatformat:1 }}")
        context = Context({'net_profit': 150, 'total_bets': 1000})
        result = template.render(context)
        self.assertEqual(result, '15.0')
    
    def test_invalid_values(self):
        """Test filters with invalid values"""
        template = Template("{% load math_filters %}{{ value|mul:multiplier }}")
        context = Context({'value': 'invalid', 'multiplier': 5})
        result = template.render(context)
        self.assertEqual(result, '0')
    
    def test_abs_value_filter(self):
        """Test absolute value filter"""
        template = Template("{% load math_filters %}{{ value|abs_value }}")
        context = Context({'value': -25})
        result = template.render(context)
        self.assertEqual(result, '25.0')
    
    def test_sub_filter(self):
        """Test subtraction filter"""
        template = Template("{% load math_filters %}{{ value|sub:amount }}")
        context = Context({'value': 100, 'amount': 30})
        result = template.render(context)
        self.assertEqual(result, '70.0')
