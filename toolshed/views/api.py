import json
from ..models import (User, UserSchema, Project, Like, ProjectSchema,
                      Comment, CommentSchema, Category, CategorySchema,
                      Group, GroupSchema, LikeSchema, LogSchema)
from flask import Blueprint, jsonify, request, abort, url_for
from ..extensions import db
from .toolshed import require_login, current_user
from datetime import datetime
from ..importer import create_project
from ..updater import update_projects


api = Blueprint('api', __name__)



# Schemas

all_users_schema = UserSchema(many=True)
single_user_schema = UserSchema()
all_projects_schema = ProjectSchema(many=True, exclude=("logs",))
all_projects_with_logs = ProjectSchema(many=True)
single_project_schema = ProjectSchema()
single_comment_schema = CommentSchema()
all_comments_schema = CommentSchema(many=True)
single_category_schema = CategorySchema()
all_categories_schema = CategorySchema(many=True)
single_group_schema = GroupSchema()
all_groups_schema = GroupSchema(many=True)
single_like_schema = LikeSchema()
all_likes_schema = LikeSchema(many=True)
all_logs_schema = LogSchema(many=True)
single_log_schema = LogSchema()

# response functions

def success_response(schema, data):
    results = schema.dump(data)
    return jsonify({"status": "success", "data": results.data})


def failure_response(reason, code):
    return jsonify({"status": "fail", "data": {"title": reason}}), code


# User routes

@api.route('/user')
def get_user():
    name = current_user()
    user = User.query.filter_by(github_name=name).first()
    if user:
        return success_response(single_user_schema, user)
    else:
        return failure_response("User not logged in", 401)


@api.route("/users")
def users():
    users = User.query.all()
    if users:
        return success_response(all_users_schema, users)
    else:
        return failure_response("There are no users.", 404)


@api.route("/users/<int:id>")
def user(id):
    user = User.query.get(id)
    if user:
        return success_response(single_user_schema, user)
    else:
        return failure_response("There was no such user.", 404)


@api.route("/users/<int:id>/pending_submissions")
def get_pending_submissions(id):
    user = User.query.get(id)
    if user.submissions:
        pending = Project.query.filter_by(submitted_by_id=user.id).filter_by(status=False).all()
        return success_response(all_projects_schema, pending)
    else:
        return failure_response("No pending submissions.", 404)


@api.route("/users/<int:id>/submissions")
def get_submissions(id):
    user = User.query.get(id)
    if user.submissions:
        submissions = Project.query.filter_by(submitted_by_id=user.id).filter_by(status=True).all()
        return success_response(all_projects_schema, submissions)
    else:
        return failure_response("No submissions.", 404)


# project routes

@api.route("/projects")
def projects():
    projects = Project.query.order_by(Project.name)
    if projects:
        return success_response(all_projects_schema, projects)
    else:
        return failure_response("There are no projects.", 404)


@api.route("/projects/newest")
def newest_projects():
    projects = Project.query.order_by(Project.date_added)
    if projects:
        return success_response(all_projects_schema, projects)
    else:
        return failure_response("There are no projects.", 404)


@api.route("/projects/popular")
def popular_projects():
    projects = Project.query.order_by(Project.score)
    if projects:
        return success_response(all_projects_schema, projects)



@api.route("/projects/<int:id>")
def project(id):
    project = Project.query.get(id)
    if project:
        return success_response(single_project_schema, project)
    else:
        return failure_response("There was no such project.", 404)


@api.route("/projects", methods=["POST"])
def make_project():
    urls = request.get_json()
    project = create_project(**urls)
    if not project:
        return failure_response("This project already exists.", 409)
    user_name = current_user()
    user = User.query.filter_by(github_name=user_name).first()
    project.submitted_by_id = user.id
    user.submissions.append(project)
    db.session.add(project)
    db.session.commit()
    return success_response(single_project_schema, project)


# Logs routes


@api.route("/projects/logs")
def projects_logs():
    projects = Project.query.all()
    if projects:
        return success_response(all_projects_with_logs, projects)
    else:
        return failure_response("There are no projects", 404)


@api.route("/projects/<int:id>/logs")
def project_logs(id):
    project = Project.query.get(id)
    if project:
        return success_response(single_project_schema, project)
    else:
        return failure_response("There was no such project.", 404)


# Group routes


@api.route("/groups")
def all_groups():
    groups = Group.query.all()
    if groups:
        return success_response(all_groups_schema, groups)
    else:
        return failure_response("There are no groups.", 404)


@api.route("/groups/<int:id>")
def group_projects(id):
    group = Group.query.get(id)
    if group.projects:
        return success_response(single_group_schema, group)
    else:
        return failure_response("There is no such group.", 404)


# Category routes

@api.route("/categories")
def all_categories():
    categories = Category.query.all()
    if categories:
        return success_response(all_categories_schema, categories)
    else:
        return failure_response("There are no categories.", 404)


@api.route("/categories/<int:id>")
def group_categories(id):
    category = Category.query.get(id)
    if category:
        return success_response(single_category_schema, category)
    else:
        return failure_response("There is no such category.", 404)


# Comment routes

@api.route("/users/<int:id>/comments")
def user_comments(id):
    user = User.query.get_or_404(id)
    if user.comments:
        return success_response(all_comments_schema, user.comments)
    else:
        return failure_response("This user has no comments.", 404)


@api.route("/projects/<int:id>/comments")
def project_comments(id):
    project = Project.query.get(id)
    if project.comments:
        return success_response(all_comments_schema, project.comments)
    else:
        return failure_response("This project has no comments.", 404)


@api.route("/projects/<int:id>/comments", methods=["POST"])
@require_login
def add_project_comment(id):
    user_name = current_user()
    user = User.query.filter_by(github_name=user_name).first()
    comment_data = request.get_json()
    project = Project.query.get(id)
    if project:
        comment = Comment(text=comment_data['text'],
                          created=datetime.utcnow(),
                          project_id=project.id,
                          user_id=user.id)

        user.comments.append(comment)
        db.session.add(comment)
        db.session.commit()
        return success_response(single_comment_schema, comment)
    else:
        return failure_response("There was no such project", 404)


@api.route("/comments/<int:id>", methods=["PUT"])
def edit_comment(id):
    user_name = current_user()
    user = User.query.filter_by(github_name=user_name).first()
    comment = Comment.query.get_or_404(id)
    comment_data = request.get_json()
    if comment.user_id != user.id:
        return failure_response("You are not authorized to edit this comment.")
    comment.text = comment_data['text']
    db.session.commit()
    return success_response(single_comment_schema, comment)



@api.route("/comments/<int:id>", methods=["DELETE"])
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    db.session.delete(comment)
    db.session.commit()
    return success_response(single_comment_schema, comment)

# Like Routes

@api.route("/likes/projects/<int:id>", methods=["POST"])
def like_project(id):
    project = Project.query.get_or_404(id)
    user_name = current_user()
    user = User.query.filter_by(github_name=user_name).first()
    new_like = Like(user_id=user.id,
                     project_id=project.id)
    user.like.append(new_like)
    db.session.add(new_like)
    db.session.commit()
    return success_response(single_like_schema, new_like)


@api.route("/likes/<int:id>", methods=["DELETE"])
def unlike_project(id):
    like = Like.query.get_or_404(id)
    db.session.delete(like)
    db.session.commit()
    return success_response(single_like_schema, like)


@api.route("/users/<int:id>/likes")
def get_user_likes(id):
    user = User.query.get_or_404(id)
    if user.likes:
        return success_response(all_likes_schema, user.likes)
    else:
        return failure_response("User has no likes", 404)


@api.route("/projects/<int:id>/likes")
def get_project_likes(id):
    project = Project.query.get_or_404(id)
    if project.user_likes:
        return success_response(all_likes_schema, project.user_likes)
    else:
        return failure_response("Project has no likes.", 404)


@api.route("/projects/update")
def update_call():
    projects = Project.query.all()
    update_projects(projects)
    return success_response()


@api.route("/projects/dump", methods=["POST"])
def projects_seed():
    urls_json = request.get_json()
