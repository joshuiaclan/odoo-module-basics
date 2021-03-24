# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class TfSchoolClasses(models.Model):
    _name = 'tf.school.classes'
    _description = 'School Class Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _STATES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ]
    _CLASS_DAYS = [
        ('mw', 'Monday, Wednesday'),
        ('tth', 'Tuesday, Thursday'),
        ('f', 'Friday')
    ]
    _SEMESTERS = [
        ('1', '1st Semester'),
        ('2', '2nd Semester'),
        ('3', '3rd Semester')
    ]
    name = fields.Char(default="Draft Class")
    description = fields.Char()
    teacher_id = fields.Many2one('tf.school.person', 'Teacher', domain=[('person_type', '=', 'teacher')])
    class_days = fields.Selection(_CLASS_DAYS, default='mw', copy=False)
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    school_year = fields.Selection([(str(num), str(num)) for num in range(1900, fields.Datetime.now().year + 1)], 'School Year',
                            default=str(fields.Date.today().year), required=True)
    semester = fields.Selection(_SEMESTERS, default='1', copy=False)
    state = fields.Selection(_STATES, default='draft', copy=False)
    student_ids = fields.Many2many('tf.school.person', string='Students', copy=False, domain=[('person_type', '=', 'student')])
    module_ids = fields.One2many('tf.school.module', 'class_id', 'Modules')
    class_id = fields.Many2one('tf.school.classes', 'Classes', ondelete='cascade')

    def class_sched_validator(self):
        class_obj = self.env['tf.school.classes']
        for rec in self:
            prompt = ''
            class_students = rec.student_ids
            class_conflicts_1 = class_obj.search([
                ('id', '!=', rec.id),
                ('class_days', '=', rec.class_days),
                ('semester', '=', rec.semester),
                ('start_time', '<=', rec.start_time),
                ('end_time', '>=', rec.start_time),
            ])
            class_conflicts_2 = class_obj.search([
                ('id', '!=', rec.id),
                ('class_days', '=', rec.class_days),
                ('semester', '=', rec.semester),
                ('start_time', '<=', rec.end_time),
                ('end_time', '>=', rec.end_time),
            ])
            class_conflicts = (class_conflicts_1 | class_conflicts_2)

            for class_student in class_students:
                for class_conflict in class_conflicts:
                    if class_student in class_conflict.student_ids:
                        # prompt += class_student.name + ' has a conflicting schedule in class ' + class_conflict.name + '.\n'
                        prompt += '%s has a conflicting schedule with class %s. \n' % \
                                  (class_student
                                   .name, class_conflict.name)

            if prompt != '':
                raise ValidationError(_(prompt))

    def action_start(self):
        self.class_sched_validator()
        if self.filtered(lambda rec: not rec.module_ids):
            raise ValidationError(_("There must be at least one module for this class."))

        if self.filtered(lambda rec: not rec.student_ids and not rec.module_ids):
            raise ValidationError(_("There must be at least one student enrolled in this class."))

        self.write({
            'name': self.env['ir.sequence'].sudo().next_by_code('tf.school.classes'),
            'state': 'in_progress'
        })

    def action_end(self):
        for rec in self:
            rec.student_ids.write({'courses_completed': [(4, rec.id)]})

        self.write({
            'state': 'done'
        })

    def unlink(self):
        if self.filtered(lambda r: r.state != 'draft'):
            raise ValidationError(_("Cannot delete. Record not in draft state."))

        return super(TfSchoolClasses, self).unlink()


class TfSchoolPerson(models.Model):
    _PERSON_TYPES = [
        ('student', 'Student'),
        ('teacher', 'Teacher')
    ]
    _name = 'tf.school.person'
    _description = 'School People'

    user_id = fields.Many2one('res.users', 'User')
    name = fields.Char(string="Name")
    address = fields.Char(string="Address")
    phone_num = fields.Char(string="Phone No.")
    email = fields.Char(string="Email")
    birthday = fields.Date(string="Date of Birth")
    age = fields.Integer(compute='_compute_age', store=True)
    person_type = fields.Selection(_PERSON_TYPES, string="Person Type", copy=False)
    courses_completed = fields.Many2many('tf.school.classes',  domain=[('state', '=', 'done')])


    @api.depends('birthday')
    def _compute_age(self):
        for rec in self:
            if rec.birthday:
                birthday = fields.Date.from_string(rec.birthday)
                today = fields.Date.from_string(fields.Date.today())
                rec.age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            else:
                rec.age = 0


class TfSchoolModule(models.Model):
    _name = 'tf.school.module'
    _description = 'School Module'

    name = fields.Char('Module Name')
    class_id = fields.Many2one('tf.school.classes', 'Class', ondelete='cascade')

