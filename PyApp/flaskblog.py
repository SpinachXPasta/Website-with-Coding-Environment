import os
from flask import Flask
from flask import render_template
from flask import request
from flask import redirect

from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.sql import expression
from flask import Flask
from flask_codemirror import CodeMirror
from flask_wtf import FlaskForm
from flask_codemirror.fields import CodeMirrorField
from wtforms.fields import SubmitField
# mandatory
CODEMIRROR_LANGUAGES = ['python', 'html']
WTF_CSRF_ENABLED = True
SECRET_KEY = 'secret'
# optional
CODEMIRROR_THEME = '3024-night'
CODEMIRROR_ADDONS = (
        ('ADDON_DIR','ADDON_NAME'),
)

#Helper class to remeber what question we are solving in IDE
class memeory:
    def __init__(self):
        self.id = 0

import ast
import copy

# The two functions below are used to execute the commands comming in from the IDE
def convertExpr2Expression(Expr):
        Expr.lineno = 0
        Expr.col_offset = 0
        result = ast.Expression(Expr.value, lineno=0, col_offset = 0)

        return result
def exec_with_return(code):
    code_ast = ast.parse(code)

    init_ast = copy.deepcopy(code_ast)
    init_ast.body = code_ast.body[:-1]

    last_ast = copy.deepcopy(code_ast)
    last_ast.body = code_ast.body[-1:]

    exec(compile(init_ast, "<ast>", "exec"), globals())
    if type(last_ast.body[0]) == ast.Expr:
        return eval(compile(convertExpr2Expression(last_ast.body[0]), "<ast>", "eval"),globals())
    else:
        exec(compile(last_ast, "<ast>", "exec"),globals())


project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "Question.db"))
database_file_2 = "sqlite:///{}".format(os.path.join(project_dir, "backup.db"))
database_file_3 = "sqlite:///{}".format(os.path.join(project_dir, "answer.db"))

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.config["SQLALCHEMY_BINDS"] = {'backup':database_file_2, 'answer':database_file_3}
app.config.from_object(__name__)
codemirror = CodeMirror(app)


db = SQLAlchemy(app)

class Question(db.Model):
    id = db.Column(db.Integer(),primary_key=True)
    question = db.Column(db.String(200), nullable=False)
    data = db.Column(db.String(200), nullable=False)
    answer = db.Column(db.String(200), nullable=False)
    isnum = db.Column(db.String(1), nullable=False)
    dif = db.Column(db.Integer(), nullable=False)

    def __repr__(self):
        return "<question: {}, data: {} ,answer: {}, isnum:{}, dif: {}>".format(self.question,self.data, self.answer,self.isnum, self.dif)

class backup(db.Model):
    __bind_key__ = 'backup'
    id = db.Column(db.Integer(),primary_key=True)
    Question_id = db.Column(db.Integer())
    question = db.Column(db.String(200), nullable=True)
    data = db.Column(db.String(200), nullable=True)
    answer = db.Column(db.String(200), nullable=True)
    isnum = db.Column(db.String(1), nullable=True)
    dif = db.Column(db.Integer(), nullable=False)

    def __repr__(self):
        return "<Question_id: {}, question: {}, data: {} ,answer: {}, isnum:{}, dif: {}>".format(self.Question_id, self.question,self.data, self.answer,self.isnum,self.dif)

class Answer(db.Model):
    __bind_key__ = 'answer'
    id = db.Column(db.Integer(),primary_key=True)
    Question_id = db.Column(db.Integer())
    answer = db.Column(db.String(2000), nullable=True)
    output = db.Column(db.String(2000), nullable=True)
    outcome = db.Column(db.String(2000), nullable=True)

    def __repr__(self):
        return "<Question_id: {}, answer: {}>, output: {}, outcome:{}".format(self.Question_id,self.answer, self.output, self.outcome)


###Backs up all the data to a second DB, remebers the prim key from first db, but saves it into a different field
def backup_data():
    print ("starting backup")
    Q = [i.id for i in backup.query.all()]
    for i in Question.query.all():
        if i not in Q:
            qa = backup(
                Question_id = i.id,
                question=i.question,
                data= i.data,
                answer=i.answer,
                isnum = i.isnum,
                dif = i.dif
                )
            db.session.add(qa)
            db.session.commit()


#If any of the needed DB's don;t exists create them
def check_create():
    if "Question.db" not in os.listdir():
        print ("createing db")
        db.create_all()
    elif "backup.db" not in os.listdir():
        print ("#$"*10)
        print ("createing backup")
        db.create_all(bind = 'backup')
    elif "answer.db" not in os.listdir():
        print ("#$"*10)
        print ("createing answer db")
        db.create_all(bind = 'answer')
    else:
        print ("Loading Db", "*"*20)


#Query

#Check the quality of data commoing in whether they satisfy our structure
def Qdcheck(request):
    allvar = ['question','data','answer','isnum','dif','id']
    for i in request:
        if i not in allvar:
            raise TypeError
    print ("*"*6)
    print (request)
    if str(type(eval(request.get("data")))) != "<class 'list'>" or str(type(eval(request.get("answer")))) != "<class 'list'>":
        raise TypeError
    for i in [request.get("data"),request.get("answer"),request.get("isnum"),request.get("question"),request.get("dif")]:
        if i == None or i == "":
            raise TypeError
    if int(request.get("dif")) > 10 or int(request.get("dif")) < 1:
        raise TypeError

# The admin page where u can manually edit and delete data with UI
@app.route('/admin', methods=["GET", "POST"])
def home():
    QA = None
    if request.form:
        try:
            print ("*******",request.form.get("question"),request.form.get("answer"))
            Qdcheck(request.form)
            qa = Question(
                question=request.form.get("question"),
                data=request.form.get("data"),
                answer=request.form.get("answer"),
                isnum = request.form.get("isnum"),
                dif = request.form.get("dif")
                )
            db.session.add(qa)
            db.session.commit()
        except Exception as e:
            print("Failed to add book")
            print(e)
    QA = Question.query.all()
    return render_template("home.html", QAS = QA)


#Home page, you can select question you want to solve
@app.route('/', methods=["GET", "POST"])
def solve():
    value = None
    link = None
    Q1 = Question.query.all()
    info = request.form.get("QA")
    l1 = None
    if info != None:
        Q2 = Question.query.filter_by(id = info).first()
        value = "Link for " + str(Q2.question)
        l1 = "pyint"
        link = str(request.base_url).replace("solve","") + "pyint"
        cell.id = info
        print ("\n\n", cell.id)
    return render_template("solve.html", QAS=Q1, value = value, link = link, l1 = l1)


#Code mirror form, for easieness of coding python
class MyForm(FlaskForm):
    source_code = CodeMirrorField(language='python', config={'lineNumbers': 'true'})
    submit = SubmitField('Submit')

#Update answer database everytime answers are inserted
def updateAns(qid,code, output,outcome):
    print ("here!")
    try:
        print ("5"*6, qid)
        qa = Answer(
            Question_id=str(qid),
            answer=str(code),
            output = str(output),
            outcome = str(outcome)
            )
        db.session.add(qa)
        db.session.commit()
    except:
        print ("failed to proces")


#Parse the code as string into objects for executing Python
def parse_code(code):
    if 'def' in code:
        fun = code.split(":")[0].split("def")[1].strip()
        funct = fun.split("(")[0]
        return funct,1
    else:
        return code,0


# Evaluate the string of code comming in for the Web page decide whether or not it passes or fails
def evalFunc(code,data,answer,isnum,qid):
    print ("preparing test")
    try:
        try:
            data = eval(data)
            answer = eval(answer)
        except:
            data = data
            answer = answer

        print (data, answer,isnum)
        print ("\n\n")
        print ("*********************************")
        print ("Python Interpreter")
        print (code)
        print ("\n\n\ Output")
        exec_with_return(code)
        ansX = None
        myf_,evaltor = parse_code(code)
        if evaltor == 1:
            myfunc_ = eval(myf_)
        else:
            myfunc_ = exec_with_return(myf_)
        if len(data) == 0:
            if evaltor == 1:
                vald = myfunc_()
            else:
                vald = myfunc_
            if isnum == 1:
                if vald == answer[0]:
                    out = True
                    print (str(qid),str(code), str(vald))
                    ansX = str(vald)
                    updateAns(qid,code, vald, "Pass")
                else:
                    out = False
                    print (str(qid),str(code), str(vald))
                    ansX = str(vald)
                    updateAns(qid,code, vald, "fail")
            else:
                if vald == answer[0]:
                    out = True
                    print (str(qid),str(code), str(vald))
                    ansX = str(vald)
                    updateAns(qid,code, vald, "Pass")
                else:
                    out = False
                    print (str(qid),str(code), str(vald))
                    ansX = str(vald)
                    updateAns(qid,code, vald, "fail")
        else:
            Success = []
            DatRun= []
            for i,j in zip(answer,data):
                if int(isnum) == 1:
                    if evaltor == 1:
                        try:
                            Success.append(i == myfunc_(*j))
                            DatRun.append(myfunc_(*j))
                        except:
                            Success.append(i == myfunc_(j))
                            DatRun.append(myfunc_(j))
                    else:
                        Success.append(i == myfunc_)
                        DatRun.append(myfunc_)
                else:
                    if evaltor == 1:
                        try:
                            Success.append(i == myfunc_(*j))
                            DatRun.append(myfunc_(*j))
                        except:
                            Success.append(i == myfunc_(j))
                            DatRun.append(myfunc_(j))
                    else:
                        Success.append(i == myfunc_)
                        DatRun.append(myfunc_)
            if len(Success) == sum(Success):
                print (str(qid),str(code), str(Success))
                updateAns(qid,code, str(DatRun), "Pass")
                ansX = str(DatRun)
                out = True
            else:
                out = False
                print (str(qid),str(code), str(Success))
                updateAns(qid,code, str(DatRun), "fail")
                ansX = str(DatRun)
        print ("*********************************")
        print ("\n\n")
        if out == True:
            return "Success",ansX
        return "Try again",ansX
    except Exception as e:
        print (str(qid),str(code), str(e))
        updateAns(qid,code, str(e), "fail")
        return str(e),"error"

#Pass message to give infromation regarding succes of code
def evMesg(answer, data,out):
    if out != "Success":
        if len(eval(data)) > 0:
            return "Given params = "+ str(data)+", corrsponding answers should be" + str(answer)
        else:
            return "No params required, answer should satisfy all items in list "+ str(answer)
    else:
        return "Congratulations"

#Pass mesasage for brief intro on question
def Intro(answer, data,out):
    print (answer, data,out)
    if len(eval(data)) > 0:
        return "Given params = "+ str(data.split(",")[0])+", corrsponding answers should be" + str(answer.split(",")[0])
    else:
        return "No params required, answer"


#Code in interpretter
@app.route('/pyint', methods=["GET", "POST"])
def pyint():
    try:
        id = cell.id
        print ("\n\n",id)
    except:
        id = 1
    QA = Question.query.filter_by(id = id).first()
    print ("\n\n")
    print (QA)
    print ("\n\n")
    data = QA.data
    answer = QA.answer
    isnum = QA.isnum
    form = MyForm()
    out = "Verdict Pedning"
    outms = "Good luck!"
    intro = Intro(answer, data,out)
    evx = None
    if form.source_code.data != None:
        text = form.source_code.data
        qid = id
        out,evx = evalFunc(text, data, answer, isnum, qid)
        outms = evMesg(answer, data,out)
    return render_template("pyint.html", QA=QA, form=form, message = out, evmsg = outms,intro = intro, evx = evx)



#Update using admin page
def Qdcheck_update(request):
    print ("*"*6)
    print (request)
    if str(type(eval(request.get("newdata")))) != "<class 'list'>" or str(type(eval(request.get("newanswer")))) != "<class 'list'>":
        raise TypeError
    for i in [request.get("newdata"),request.get("newanswer"),request.get("newisnum"),request.get("newquestion"),request.get("newdif")]:
        if i == None or i == "":
            raise TypeError
    if int(request.get("newdif")) > 10 or int(request.get("newdif")) < 1:
        raise TypeError

@app.route("/update", methods=["POST"])
def update():
    try:
        print (request.form)
        Qdcheck_update(request.form)
        id = request.form.get("id")
        newquestion = request.form.get("newquestion")
        oldquestion = request.form.get("oldquestion")
        newdata = request.form.get("newdata")
        olddata = request.form.get("olddata")
        newanswer = request.form.get("newanswer")
        oldanswer = request.form.get("oldanswer")
        oldisnum = request.form.get("oldisnum")
        newisnum = request.form.get("newisnum")
        olddif = request.form.get("olddif")
        newdif = request.form.get("newdif")
        Query = Question.query.filter_by(id = id).first()
        print (Query)
        Query.question = newquestion
        Query.data = newdata
        Query.answer = newanswer
        Query.isnum = newisnum
        Query.dif = newdif
        db.session.commit()
    except Exception as e:
        print("Couldn't update book title")
        print(e)
    return redirect("/admin")

# Delete using admin page
@app.route("/delete", methods=["POST"])
def delete():
    backup_data()
    id = request.form.get("id")
    Query = Question.query.filter_by(id = id).first()
    db.session.delete(Query)
    db.session.commit()
    return redirect("/admin")






from flask import jsonify
#### APIS
#adding variables
# Main API for interacting with QUestions DB

def Qdcheck_api(req):
    if id == "" or id == None:
        raise TypeError
    Qs = ['question','data','answer','isnum','dif']
    allvar = ['question','data','answer','isnum','dif','id']

    print (req)
    for i in req:
        print (i)
        print (req.get(i))
        if i != 'id':
            if i not in allvar:
                raise TypeError
            extract = req.get(i)
            print (extract)
            if extract == None or extract == "":
                print ("In trubs")
                raise TypeError
            print ("W")
            print (i)
            if i == 'data' or i == 'answer':
                print ("e")
                print (str(type(eval(extract))))
                if str(type(eval(extract))) != "<class 'list'>":
                    raise TypeError
            if i == 'dif':
                if int(extract)<0 or int(extract) > 100:
                    raise TypeError

@app.route('/api' , methods = ['GET','POST','PUT','DELETE'])
def api():
    try:
        if request.method == 'GET':
            out = []
            Query = Question.query.all()
            for i in Query:
                out.append( {'id':i.id, 'question':i.question})
            return jsonify(out)
        if request.method == 'POST':
            try:
                Qdcheck(request.args)
                qa = Question(
                    question=request.args.get("question"),
                    data=request.args.get("data"),
                    answer=request.args.get("answer"),
                    isnum = request.args.get("isnum"),
                    dif = request.args.get("dif")
                    )
                db.session.add(qa)
                db.session.commit()
            except Exception as e:
                return("\n\n Failed to add book \n\n")
            return "\n\n success \n\n"
        if request.method == 'PUT':
            try:
                if request.args.get("id") == None:
                    return "please include row id"
                id = request.args.get("id")
                print ("*")
                Qdcheck_api(request.args)
                print ("*")
                Query = Question.query.filter_by(id = id).first()
                for i in request.args:
                    if i != 'id':
                        new_data = request.args.get(i)
                        print (new_data)
                        if i == "question":
                            Query.question = new_data
                        if i == "data":
                            Query.data = new_data
                        if i == "answer":
                            Query.answer = new_data
                        if i == "isnum":
                            Query.isnum = new_data
                        if i == "dif":
                            Query.dif = new_data
                        db.session.commit()
                        print (i)
            except Exception as e:
                return("\n\n Failed to add book \n\n")
            return "\n\n success \n\n"
        if request.method == 'DELETE':
            try:
                qid = request.args.get("qid")
                backup_data()
                id = qid
                Query = Question.query.filter_by(id = id).first()
                db.session.delete(Query)
                db.session.commit()
                return {'id':id, 'status':'removed'}
            except:
                return "failed"
    except:
        return {'error':'invalid call'}



#API to view backup db
@app.route('/api_backup' , methods = ['GET'])
def api_backup():
    if request.method == 'GET':
        out = []
        Query = backup.query.all()
        for i in Query:
            out.append( {'backup_id':i.id, 'question_id': i.Question_id, 'question':i.question})
        return jsonify(out)




#Evaluate code comming in as API and send back answer
def evalFunc_Json(code,data,answer,isnum,qid):
    try:
        try:
            data = eval(data)
            answer = eval(answer)
        except:
            data = data
            answer = answer
        exec_with_return(code)
        myf_,evaltor = parse_code(code)
        ansX = []
        if evaltor == 1:
            myfunc_ = eval(myf_)
        else:
            myfunc_ = exec_with_return(myf_)
        if len(data) == 0:
            if evaltor == 1:
                vald = myfunc_()
            else:
                vald = myfunc_
            if isnum == 1:
                if vald == answer[0]:
                    updateAns(qid,code, vald, "Pass")
                    ansX = str(vald)
                    return {"qid":qid, "code":code, "vald":vald,"outcome":"Pass"}
                else:
                    updateAns(qid,code, vald, "fail")
                    ansX = str(vald)
                    return {"qid":qid, "code":code, "vald":vald,"outcome":"fail"}
            else:
                if vald == answer[0]:
                    updateAns(qid,code, vald, "Pass")
                    ansX = str(vald)
                    return {"qid":qid, "code":code, "vald":vald,"outcome":"Pass"}
                else:
                    print (str(qid),str(code), str(vald))
                    ansX = str(vald)
                    return {"qid":qid, "code":code, "vald":vald,"outcome":"fail"}
        else:
            Success = []
            DatRun = []
            for i,j in zip(answer,data):
                if int(isnum) == 1:
                    if evaltor == 1:
                        try:
                            Success.append(i == myfunc_(*j))
                            DatRun.append(myfunc_(*j))
                        except:
                            Success.append(i == myfunc_(j))
                            DatRun.append(myfunc_(j))
                    else:
                        Success.append(i == myfunc)
                        DatRun.append(myfunc)
                else:
                    if evaltor == 1:
                        try:
                            Success.append(i == myfunc_(j))
                            DatRun.append(myfunc_(j))
                        except:
                            Success.append(i == myfunc_(*j))
                            DatRun.append(myfunc_(*j))
                    else:
                        Success.append(i == myfunc_)
                        DatRun.append(myfunc_)

            if len(Success) == sum(Success):
                updateAns(qid,code, str(Success), "Pass")
                return {"qid":qid, "code":code, "vald":str(DatRun),"outcome":"Pass"}
            else:
                out = False
                updateAns(qid,code, str(Success), "fail")
                return {"qid":qid, "code":code, "vald":str(DatRun),"outcome":"fail"}
    except Exception as e:
        updateAns(qid,code, str(e), "fail")
        return {"qid":qid, "code":code, "vald":str(e),"outcome":"fail"}


# API to veiw answers doc
@app.route('/api_answer' , methods = ['GET','POST'])
def api_answer():
    try:
        if request.method == 'GET':
            out = []
            Query = Answer.query.all()
            print (Query)
            for i in Query:
                out.append( {'answer_id':i.id,'Question_id':i.Question_id, 'answer': i.answer, 'output':i.output,'outcome':i.outcome })
            return jsonify(out)
        if request.method == 'POST':
            try:
                print ("\n\n\n")
                print (request.args)
                id = request.args.get("question_id")
                text = request.args.get("code")
                print ("*"* 10)
                print (id,text)
                QA = Question.query.filter_by(id = id).first()
                data = QA.data
                answer = QA.answer
                isnum = QA.isnum
                qid = id
                out = evalFunc_Json(text, data, answer, isnum, qid)
                return out
            except:
                print ("failed to complete")
    except:
        return {'error':'invalid call'}





if __name__ == "__main__":
    cell = memeory()
    check_create()
    backup_data()
    app.run(debug=True)
