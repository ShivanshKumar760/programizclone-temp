from flask import Flask , request , jsonify
import os
import tempfile
import subprocess
import psycopg
app = Flask(__name__)
DATABASE_URL=os.environ("DATABASE_URL")

@app.route("/",methods=["GET"])
def health():
    return jsonify({"status":"Ok"})


@app.route("/signup",methods=["POST"])
def signup():
    data = request.get_json()
    #data = {"name":"Shivansh","password":"1234"}
    name = data.get("name") #Shivansh
    password = data.get("password")#1234

    conn = psycopg.connect(DATABASE_URL)
    #Cursor-basically points to the currenct connection
    cur = conn.cursor()
    #SQL templating
    cur.execute("INSERT INTO <table_name> (name,password) VALUES (%s,%s)",(name,password),)
    row = cur.fetchone()


@app.route("/signin",methods=["POST"])
def signin():
    conn = psycopg.connect(DATABASE_URL)


@app.route("/execute",methods=["POST"])
def execute():
    data = request.get_json()
    #data={"code":"print('Hello')"}
    code = data.get("code")
    #code = "print('Hello')"

    if not code:
        return jsonify(error="Please provide code to run")

    tmp_dir = tempfile.mkdtemp() # mkdir in ur computer which u use to create folder
    #/Users/shivansh-mac/Desktop/development/python-backend/01.flask/02.programiz-clone/tmp_dir/script.py
    script_path = os.path.join(tmp_dir,"script.py") # script.py

    file = open(script_path,"w")
    file.write(code)
    file.close()

    #cwd : current working directory 
    result = subprocess.run(
        ["python","script.py"],
        cwd=tmp_dir,
        capture_output=True,#Buffer data-non readable form 
        text=True
    )

    print(result)
    #CompletedProcess(args=['python', 'script.py'], returncode=0, stdout='hello world\n', stderr='')

    return jsonify({"message":"Success","stdout":result.stdout}) 

if __name__ == "__main__":
    app.run()