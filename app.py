from flask import Flask , request , jsonify
import os
import tempfile
import subprocess
app = Flask(__name__)


@app.route("/",methods=["GET"])
def health():
    return jsonify({"status":"Ok"})


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