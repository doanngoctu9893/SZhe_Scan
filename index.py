# -*- coding:utf-8 -*-
from flask import  render_template, request, redirect, url_for, session, flash
import uuid
from models import User, Log, BaseInfo, InvitationCode,BugList,POC,IPInfo,DomainInfo,Profile
from exts import db
from init import app,redispool
# from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor
from SZheConsole import SZheConsole
from POCScan import selfpocscan
# executor = ThreadPoolExecutor()
executor = ProcessPoolExecutor()


def GetBit():
    #获取数据库中各个漏洞的数量
    seriouscount = BugList.query.filter(BugList.buggrade=='serious').count()
    highcount = BugList.query.filter(BugList.buggrade=='high').count()
    mediumcount = BugList.query.filter(BugList.buggrade=='medium').count()
    lowcount = BugList.query.filter(BugList.buggrade=='low').count()
    allcount=seriouscount+highcount+mediumcount+lowcount
    sqlcount=BugList.query.filter(BugList.bugname=='SQLBugScan').count()
    comincount=BugList.query.filter(BugList.bugname=='ComInScan').count()
    weblogiccount=BugList.query.filter(BugList.bugname=='WebLogicScan').count()
    fileincount=BugList.query.filter(BugList.bugname=='FileIncludeScan').count()
    sendircount=BugList.query.filter(BugList.bugname=='SenDir').count()
    robotscount=BugList.query.filter(BugList.bugname=='robots文件发现').count()
    phpinfocount=BugList.query.filter(BugList.bugname=='phpstudy探针').count()
    gitcount=BugList.query.filter(BugList.bugname=='git源码泄露扫描').count()
    phpstudycount=BugList.query.filter(BugList.bugname=='phpstudy phpmyadmin默认密码漏洞').count()
    otherpoc=allcount-sqlcount-comincount-weblogiccount-fileincount-sendircount-robotscount-phpinfocount-gitcount
    bugbit={
        'seriouscount':seriouscount,
        'highcount':highcount,
        'mediumcount':mediumcount,
        'lowcount':lowcount,
        'allcount': allcount,
    }
    bugtype={
        'SQLBugScan':sqlcount,
        'ComInScan':comincount,
        'WebLogicScan':weblogiccount,
        'FileIncludeScan':fileincount,
        'SenDir':sendircount,
        'robots文件发现':robotscount,
        'phpstudy探针':phpinfocount,
        'git源码泄露扫描':gitcount,
        'phpstudy phpmyadmin默认密码漏洞':phpstudycount,
        'POC扫描漏洞':otherpoc
    }
    return bugbit,bugtype

def save_log(ip, email):
    log = Log(ip=ip, email=email)
    db.session.add(log)
    db.session.commit()


def validate(email, username, password1, password2):
    user_email = User.query.filter(User.email == email).first()
    user_name = User.query.filter(User.username == username).first()
    if user_email:
        return "邮箱已被注册"
    elif len(username) < 4:
        return "用户名长度至少四个字符"
    elif user_name:
        return "用户名已被注册"
    elif len(password1) < 6:
        return "密码长度至少6个字符"
    elif password1 != password2:
        return "两次密码输入不一致"
    else:
        return


'''
    输入的url格式应该为:www.baidu.com或者127.0.0.1形式
'''


@app.route('/<int:page>',methods=['GET'])
@app.route('/')
# @login_required
def index(page=None):
    bugbit,bugtype=GetBit()
    if not page:
        page = 1
    per_page = 10
    print(bugbit['allcount'])
    paginate = BaseInfo.query.order_by(BaseInfo.date.desc()).paginate(page, per_page, error_out=False)
    infos = paginate.items
    return render_template('homeOne.html', paginate=paginate, infos=infos,bugbit=bugbit,bugtype=bugtype)


@app.route('/POCmanage',methods=['GET','POST'])
# @login_required
def POCmanage():
    bugbit = GetBit()
    if request.method == 'GET':
        return render_template('pocmanage.html',bugbit=bugbit)
    else:
        pocname=request.form.get('pocname')
        rule=request.form.get('rule')
        expression=request.form.get('expression')
        buggrade=request.form.get('buggrade')
        redispool.hset('bugtype', pocname, buggrade)
        poc = POC(name=pocname, rule=rule, expression=expression)
        db.session.add(poc)
        db.session.commit()
        return render_template('pocmanage.html',bugbit=bugbit)


@app.route('/setting')
# @login_required
def setting():
    bugbit = GetBit()
    return render_template('setting.html',bugbit=bugbit)


@app.route('/editinfo',methods=['GET','POST'])
# @login_required
def editinfo():
    user_id = session.get('user_id')
    nowuser = User.query.filter(User.id == user_id).first()
    username = nowuser.username
    if request.method == 'GET':
        profile=Profile.query.filter(Profile.userid == user_id).first()
        if not profile:
            signature=""
            blog=""
        else:
            signature=profile.signature
            blog = profile.blog
        return render_template('user-infor.html',username=username,blog=blog,signature=signature)
    else:
        blog=request.form.get('blog')
        signature=request.form.get('signature')
        oldpassword=request.form.get('oldpassword')
        password1=request.form.get('password1')
        password2=request.form.get('password2')
        if nowuser.check_password(oldpassword):
            if password1!=password2:
                flash("两次密码输入不一致 :D")
                return render_template('user-infor.html')
            else:
                profile = Profile.query.filter(Profile.userid == user_id).first()
                if not profile:
                    temp=Profile(userid=user_id,blog=blog,signature=signature)
                    db.session.add(temp)
                elif blog!="" and signature!="":
                    profile.blog=blog
                    profile.signature=signature
                nowuser.set_password(password1)
                db.session.commit()
                return redirect(url_for('user'))
        else:
            flash("旧密码输入错误 :(")
            return render_template('user-infor.html',username=username,blog=blog,signature=signature)


@app.route('/domaindetail/<int:id>',methods=['GET'])
@app.route('/domaindetail')
# @login_required
def domaindetail(id=None):
    if not id:
        baseinfo = BaseInfo.query.order_by(BaseInfo.id.desc()).first()
    else:
        baseinfo = BaseInfo.query.filter(BaseInfo.id == id).first()
    if baseinfo.boolcheck:
        deepinfo =IPInfo.query.filter(IPInfo.baseinfoid == baseinfo.id).first()
    else:
        deepinfo=DomainInfo.query.filter(DomainInfo.baseinfoid == baseinfo.id).first()
    buglist=BugList.query.filter(BugList.oldurl == baseinfo.url).all()
    return render_template('domain-detail.html',baseinfo=baseinfo,deepinfo=deepinfo,buglist=buglist)


@app.route('/buglist/<int:page>',methods=['GET'])
@app.route('/buglist')
# @login_required
def buglist(page=None):
    bugbit = GetBit()
    if not page:
        page = 1
    per_page = 10
    paginate = BugList.query.order_by(BugList.id.desc()).paginate(page, per_page, error_out=False)
    bugs = paginate.items
    return render_template('bug-list.html', paginate=paginate, bugs=bugs,bugbit=bugbit)


@app.route('/bugdetail/<int:id>',methods=['GET'])
@app.route('/bugdetail')
# @login_required
def bugdetail(id=None):
    if not id:
        buginfo = BugList.query.order_by(BugList.id.desc()).first()
    else:
        buginfo = BugList.query.filter(BugList.id == id).first()
    oldurlinfo=BaseInfo.query.filter(BaseInfo.url==buginfo.oldurl).first()
    return render_template('bug-details.html',buginfo=buginfo,oldurlinfo=oldurlinfo)


@app.route('/user', methods=['GET', 'POST'])
# @login_required
def user():
    allcode=InvitationCode.query.order_by(InvitationCode.id.desc()).limit(10).all()
    user_id = session.get('user_id')
    nowuser = User.query.filter(User.id == user_id).first()
    username = nowuser.username
    profile = Profile.query.filter(Profile.userid == user_id).first()
    if request.method == 'GET':
        return render_template('user-center.html',allcode=allcode,username=username,profile=profile)
    else:
        return render_template('user-center.html',allcode=allcode,username=username,profile=profile)


@app.route('/test_console', methods=['GET', 'POST'])
# @login_required
def console():
    bugbit = GetBit()
    if request.method == 'GET':
        return render_template('console.html',bugbit=bugbit)
    else:
        urls = request.form.get('urls')
        executor.submit(SZheConsole, urls)
        return render_template('console.html',bugbit=bugbit)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('sign_in.html')
    else:
        email = request.form.get('email')
        remeber = request.form.get('remeber')
        password=request.form.get('password')
        save_log(request.remote_addr, email)
        user = User.query.filter(User.email == email).first()
        if user and user.check_password(password):
            if remeber:
                session.permanent = True
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            flash("邮箱或密码输入错误")
            return render_template('sign_in.html')


# 生成邀请码
@app.route('/GenInvitationCode', methods=['GET', 'POST'])
# @login_required
def GenInvitationCode():
    code = str(uuid.uuid1())
    Code = InvitationCode(code=code)
    db.session.add(Code)
    db.session.commit()
    allcode=InvitationCode.query.order_by(InvitationCode.id.desc()).limit(10).all()
    return render_template("user-center.html", temp=Code.code,allcode=allcode)


@app.route('/regist/', methods=['GET', 'POST'])
def regist():
    if request.method == 'GET':
        return render_template('sign_up.html')
    else:
        email = request.form.get('email')
        username = request.form.get('username')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        invitationcode = request.form.get('invitationcode')
        # 邮箱和用户名验证
        message = validate(email, username, password1, password2)
        # 邀请码验证
        IsCode = InvitationCode.query.filter(InvitationCode.code == invitationcode).first()

        if message:
            flash(message)
            return render_template('sign_up.html')
        elif not IsCode:
            flash("邀请码错误")
            return render_template('sign_up.html')
        else:
            user = User(email=email, username=username, password=password1)
            db.session.add(user)
            db.session.delete(IsCode)
            db.session.commit()
            return redirect(url_for('login'))


@app.route('/logout/')
# @login_required
def logout():
    # session.pop('user_id')
    # del session('user_id')
    session.clear()
    return redirect(url_for('login'))


@app.route('/about/')
# @login_required
def about():
    return render_template('about.html')


# 日志每页显示38条
@app.route('/log_detail/')
@app.route('/log_detail/<int:page>', methods=['GET'])
# @login_required
def log_detail(page=None):
    bugbit = GetBit()
    if not page:
        page = 1
    per_page = 38
    paginate = Log.query.order_by(Log.date.desc()).paginate(page, per_page, error_out=False)
    logs = paginate.items
    return render_template('log_detail.html', paginate=paginate, logs=logs,bugbit=bugbit)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/test500')
def test500():
    return render_template('500.html')


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.context_processor
def my_comtext_processor():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.filter(User.id == user_id).first()
        if user:
            return {'user': user}
    return {}


if __name__ == '__main__':
    app.run()
