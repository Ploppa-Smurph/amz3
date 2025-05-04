from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import Report, User, Note, Tag
from app.blueprints.reports import reports_bp
from app import db
from app.forms import ReportForm

# Existing routes
@reports_bp.route('/all_manager_reports')
@login_required
def all_manager_reports():
    """For admins only: Displays a list of reports created by manager users."""
    if current_user.role != 'admin':
        flash("You do not have permission to view this page.", "danger")
        return redirect(url_for('home'))
    manager_reports = Report.query.join(Report.author).filter(User.role == 'manager').all()
    return render_template('all_manager_reports.html', reports=manager_reports)

@reports_bp.route('/all_user_reports')
@login_required
def all_user_reports():
    """For admins and managers: Displays a list of reports created by user-level users."""
    if current_user.role not in ['admin', 'manager']:
        flash("You do not have permission to view this page.", "danger")
        return redirect(url_for('home'))
    user_reports = Report.query.join(Report.author).filter(User.role == 'user').all()
    return render_template('all_user_reports.html', reports=user_reports)

# New routes: Manage Reports, Edit Report, Delete Report

@reports_bp.route('/manage', methods=["GET"])
@login_required
def manage_reports():
    """
    For admins only: Display a page that lists all reports so that
    reports can be edited or deleted.
    """
    if current_user.role != 'admin':
        flash("You do not have permission to view this page.", "danger")
        return redirect(url_for("home"))
    reports = Report.query.order_by(Report.date_posted.desc()).all()
    return render_template("admin/manage_reports.html", reports=reports)

@reports_bp.route('/edit/<int:report_id>', methods=["GET", "POST"])
@login_required
def edit_report(report_id):
    """
    For admins only: Edit an existing report.
    """
    if current_user.role != 'admin':
        flash("You do not have permission to edit reports.", "danger")
        return redirect(url_for("home"))
    report = Report.query.get_or_404(report_id)
    form = ReportForm(obj=report)
    if form.validate_on_submit():
        report.title = form.title.data
        report.notes = form.notes.data
        if form.image.data:
            report.image_data = form.image.data.read()
            report.image_mimetype = form.image.data.mimetype
        try:
            db.session.commit()
            flash("Report updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash("Error updating report: " + str(e), "danger")
        return redirect(url_for("reports.manage_reports"))
    return render_template("admin/edit_report.html", form=form, report=report)

@reports_bp.route('/delete/<int:report_id>', methods=["GET", "POST"])
@login_required
def delete_report(report_id):
    """
    For admins only: Delete an existing report.
    To delete a report, the admin must confirm the deletion by entering their password.
    """
    if current_user.role != 'admin':
        flash("You do not have permission to delete reports.", "danger")
        return redirect(url_for("home"))
    report = Report.query.get_or_404(report_id)
    if request.method == "POST":
        password = request.form.get("password")
        if not current_user.check_password(password):
            flash("Incorrect password. Report not deleted.", "danger")
            return render_template("admin/delete_report.html", report=report)
        try:
            db.session.delete(report)
            db.session.commit()
            flash("Report deleted successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash("Error deleting report: " + str(e), "danger")
        return redirect(url_for("reports.manage_reports"))
    return render_template("admin/delete_report.html", report=report)