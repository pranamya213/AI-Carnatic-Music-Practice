from flask import Blueprint, render_template

# Create a blueprint for the main routes
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Route for the landing page."""
    return render_template('index.html')
