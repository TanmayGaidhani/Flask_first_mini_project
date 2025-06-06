from flask import Flask, render_template, request,session,redirect
from flask_sqlalchemy import SQLAlchemy
import json
from werkzeug.utils import secure_filename
from datetime import datetime
from pathlib import Path
from flask_mail import Mail,Message  # for adding mail
import os 
import math


config_path = Path(__file__).parent / 'templates' / 'config.json'
print(f"Looking for config at: {config_path}")

with open(config_path, 'r', encoding='utf-8') as c:
    content = c.read()

params = json.loads(content)["params"]

local_server = params.get("local_server", True)
app = Flask(__name__) 
app.config['UPLOAD_FOLDER'] = params['upload_location']

app.secret_key = 'the random string'

app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = 587,
    MAIL_USE_TLS = True,
    MAIL_USERNAME = params['gmail_user'],
    MAIL_PASSWORD = params['gmail_password'],
)

mail=Mail(app)

if local_server: 
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To suppress warning
db = SQLAlchemy(app)

class Contacts(db.Model):
    '''
    sr, name, email, phone_num, mes, date
    '''
    sr = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    mes = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(20), nullable=True, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class Posts(db.Model):
    __tablename__ = 'posts'
    sr = db.Column(db.Integer, primary_key=True)  # Matches your database
    title = db.Column(db.String(100))
    slug = db.Column(db.String(100), unique=True)  # Make unique but not primary key
    tagline = db.Column(db.Text)
    content = db.Column(db.Text)
    img_file = db.Column(db.String(100))
    date = db.Column(db.DateTime)
    


@app.route('/')
def home():
    # Pagintaion logic
    posts = Posts.query.filter_by().all()
    # [0:params['no_of_posts']]
    last = math.ceil(len(posts) / int(params['no_of_posts']))

    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    else:
        page = int(page) 

    posts = posts[(page-1) * int(params['no_of_posts']) : page * int(params['no_of_posts'])]

    if (page ==1):
        prev = "#"
        next = "/?page="+str(page+1)
    elif(page == last):
        prev = "/?page="+str(page-1)
        next = "#"
    else:
        prev = "/?page="+str(page-1)
        next = "/?page="+str(page+1)

    return render_template("index.html", params=params, posts=posts, prev=prev ,next =next)




@app.route('/about')
def about():
    return render_template("about.html", params=params)



@app.route('/dashboard', methods=['GET', 'POSt'])
def dashboard():
    if ('user' in session and session['user'] == params['admin_user']):
        posts = Posts.query.all()
        return render_template('dashboard.html',params=params,posts=posts)
    



    # admin usersathi single id and password
    if request.method == 'POST':
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        if(username == params['admin_user'] and userpass == params['admin_password']):
            # set the session variable
            # database madhun data aananya sathi 
            posts = Posts.query.all()
            session['user'] = username 
            return render_template('dashboard.html', params=params,posts=posts)
    
    return render_template("login.html", params=params)


@app.route("/post/<string:slug>", methods= ["GET"])
def post_route(slug):
    post = Posts.query.filter_by(slug=slug).first()
    posts = Posts.query.all()
    print("All post slugs:", [p.slug for p in posts])

    if not post:
        return "Post not found", 404
    return render_template("post.html", post=post, params=params )



@app.route('/posts')
def all_posts():
    posts = Posts.query.all()
    return render_template('posts.html',params=params, posts=posts)



@app.route('/edit/<string:sr>', methods=['GET', 'POST'])
def edit(sr):
    if 'user' in session and session['user'] == params['admin_user']:
        date = datetime.now()

        if request.method == 'POST':
            box_title = request.form.get('title')
            tagline = request.form.get('tagline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')

            if sr == '0':  # Add new post
                post = Posts(title=box_title, slug=slug, content=content,
                             tagline=tagline, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
                db.session.refresh(post)  # Ensures post.sr is available
                return redirect(f"/edit/{post.sr}")
            else:  # Edit existing post
                post = Posts.query.filter_by(sr=sr).first()
                if post:
                    post.title = box_title
                    post.slug = slug
                    post.content = content
                    post.tagline = tagline
                    post.img_file = img_file
                    post.date = date
                    db.session.commit()
                return redirect(f"/edit/{sr}")

        post = None if sr == '0' else Posts.query.filter_by(sr=sr).first()
        return render_template('edit.html', params=params, post=post, sr=sr)


@app.route('/uploader', methods=['GET', 'POST'])
def uploader():
    if ('user' in session and session['user'] == params['admin_user']):
        if (request.method == 'POST'):
            f=request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "UPLOADED SUCCESSFULLY"
       


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        '''ADD ENTRY IN DATABASE'''
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        entry = Contacts(name=name, email=email, phone_num=phone, mes=message,
                         date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        db.session.add(entry)
        db.session.commit()
        mail.send_message('new Message from '+name,
                           sender = params['gmail_user'],
                           recipients=[params['gmail_user']],
                           body = message+"\n"+ phone
                           )


    return render_template("contact.html", params=params)

# DELETE 
@app.route('/delete/<string:sr>',methods=['GET', 'POST'])
def delete(sr):
    if ('user' in session and session['user'] == params['admin_user']):
        post = Posts.query.filter_by(sr=sr).first() 
        db.session.delete(post)
        db.session.commit()
    return redirect("/dashboard")


# LOGOUT ROUT
@app.route('/logout')
def logout():
    session.pop('user')
    return redirect("/dashboard")




# if __name__ == '__main__':
    # app.run(debug=True)
if __name__ == '__main__':
    app.run(debug=True)
