import os
from os.path import join, dirname
from dotenv import load_dotenv

from flask import Flask, render_template, jsonify, request, redirect, url_for
from pymongo import MongoClient
import jwt
import datetime
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from bson.objectid import ObjectId


app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["UPLOAD_FOLDER"] = "./static/myassets/profile"

SECRET_KEY = "SNAPDARGON"

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)

db = client[DB_NAME]


@app.route('/')
def home():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]},)
        return redirect(url_for("dashboard"))
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Your token has expired"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="There was problem logging you in"))

@app.route("/login")
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

@app.route("/sign_in", methods=["POST"])
def sign_in():
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.users.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    if result:
        payload = {
            "id": username_receive,
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "Your username or password does not match",
            }
        )

@app.route('/dashboard')
def dashboard():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        user_kls = db.kelas_mhs.count_documents({"username": user_info['username']})
        mhs_kls = db.kelas_mhs.count_documents({"nim": user_info['username']})
        role = user_info.get('role', 'user')
        count_mahasiswa = db.users.count_documents({'role': 'mahasiswa'})
        count_dosen = db.users.count_documents({'role': 'dosen'})
        count_matkul = db.matakuliah.count_documents({})
        count_kelas = db.kelas_mhs.count_documents({})
        return render_template('dashboard.html', user_info=user_info, active_page='dashboard', role=role, count_mahasiswa=count_mahasiswa, count_dosen=count_dosen, count_matkul=count_matkul, user_kls=user_kls, mhs_kls=mhs_kls, count_kelas=count_kelas)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    
@app.route('/manajemen-dosen')
def mnjmdosen():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        if user_info and user_info.get('role') in ['superuser']:
            semua_dosen = list(db.users.find({'role': 'dosen'}))
            for user in semua_dosen:
                user['_id'] = str(user['_id'])
            return render_template("admin/mnjmdosen.html", dosen=semua_dosen, active_page="mnjm_dosen", user_info=user_info)
        else:
            return redirect(url_for("home"))
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    
@app.route('/manajemen-dosen/checknip', methods=['POST'])
def check_nip():
    nip_receive = request.form['nip_give']
    exists = bool(db.users.find_one({"username": nip_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/manajemen-dosen/savedosen', methods=['POST'])
def savedosen():
    nip_receive = request.form['nip']
    password_receive = 'Dosen@123'
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    fname_receive = request.form['fname']
    tl_receive = request.form['tl']
    gender_receive = request.form['gender']

    doc = {
        "username": nip_receive,
        "password": password_hash,
        "role": "dosen",
        "full_name": fname_receive,
        "tanggal_lahir": tl_receive,
        "gender": gender_receive,
        "profile_pic": "2.jpg",                                         
        "profile_pic_real": "myassets/profile/2.jpg",
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/editdosen/<string:id>', methods=['GET', 'POST'])
def editdosen(id):
    if request.method == 'POST':
        fname_receive = request.form['name']
        tl_receive = request.form['date']
        gender_receive = request.form['gender']

        db.users.update_one({'_id': ObjectId(id)}, {'$set': {'full_name': fname_receive, 'tanggal_lahir': tl_receive, 'gender': gender_receive}})
        return jsonify({'result' : 'success'})
    
    token_receive = request.cookies.get("mytoken")
    try:
        data = db.users.find_one({'_id': ObjectId(id)})

        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        selected_gender = data.get('gender', 'male')
        return render_template('admin/editdosen.html', data=data, active_page="mnjm_dosen",selected_gender=selected_gender, user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/deletedosen/<string:id>', methods=["POST"])
def delete(id):
    db.users.delete_one({'_id': ObjectId(id)})
    return jsonify({"result": "success"})

@app.route('/manajemen-mahasiswa')
def mnjm_mhs():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        semua_mhs = list(db.users.find({'role': 'mahasiswa'}))
        for user in semua_mhs:
            user['_id'] = str(user['_id'])
        return render_template("admin/mnjmmahasiswa.html", active_page="mnjm_mhs", user_info=user_info, semua_mhs=semua_mhs)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))    

@app.route('/manajemen-mahasiswa/checknim', methods=['POST'])
def check_nim():
    nim_receive = request.form['nim_give']
    exists = bool(db.users.find_one({"username": nim_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/manajemen-mahasiswa/savemhs', methods=['POST'])
def savemhs():
    nim_receive = request.form['nim']
    password_receive = 'Mahasiswa@123'
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    fname_receive = request.form['fnamemhs']
    tl_receive = request.form['tlmhs']
    gender_receive = request.form['gendermhs']
    idOrtu_receive = request.form['idOrtu']
    fnameortu_receive = request.form['fnamemhsortu']

    doc = {
        "username": nim_receive,
        "password": password_hash,
        "role": "mahasiswa",
        "full_name": fname_receive,
        "tanggal_lahir": tl_receive,
        "gender": gender_receive,
        "id_ortu": idOrtu_receive,
        "fname_ortu": fnameortu_receive,
        "profile_pic": "",                                         
        "profile_pic_real": "myassets/profile/2.jpg",
    }

    docortu = {
        "username": idOrtu_receive,
        "password": password_hash,
        "role": "orangtua",
        "full_name": fnameortu_receive,
        "profile_pic": "",                                         
        "profile_pic_real": "myassets/profile/2.jpg",
    }

    db.users.insert_one(doc)
    db.users.insert_one(docortu)
    return jsonify({'result': 'success'})

@app.route('/editmhs/<string:id>', methods=['GET', 'POST'])
def editmhs(id):
    if request.method == 'POST':
        fname_receive = request.form['name']
        tl_receive = request.form['date']
        gender_receive = request.form['gender']
        fnameortu_receive = request.form['nameortu']

        db.users.update_one({'_id': ObjectId(id)}, {'$set': {'full_name': fname_receive, 'tanggal_lahir': tl_receive, 'gender': gender_receive, 'fname_ortu' : fnameortu_receive}})
        return jsonify({'result': 'success'})

    token_receive = request.cookies.get("mytoken")
    try:
        data = db.users.find_one({'_id': ObjectId(id)})

        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        selected_gender = data.get('gender', 'male')
        return render_template('admin/editmhs.html', data=data, active_page="mnjm_mhs",selected_gender=selected_gender, user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/deletemhs/<string:id>', methods=["POST"])
def deletemhs(id):
    db.users.delete_one({'_id': ObjectId(id)})
    return jsonify({"result": "success"})

@app.route('/manajemen-matakuliah')
def mnjmmatakuliah():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        semua_matkul = list(db.matakuliah.find())
        for matkul in semua_matkul:
            matkul['_id'] = str(matkul['_id'])
        return render_template("admin/mnjmmatakuliah.html", active_page="mnjm_matkul", user_info=user_info, semua_matkul=semua_matkul)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/manajemen-matkul/checkkdm', methods=['POST'])
def check_kdm():
    kdm_receive = request.form['kdm']
    exists = bool(db.matakuliah.find_one({"username": kdm_receive}))
    return jsonify({'result': 'success', 'exists': exists})

@app.route('/manajemen-mahasiswa/savematkul', methods=['POST'])
def savematkul():
    kdm_receive = request.form['kdm']
    matkul_receive = request.form['matkul']
    pilihjurusan_receive = request.form['pilihjurusan']

    doc = {
        "Kode_Matkul": kdm_receive,
        "Nama_Matkul": matkul_receive,
        "Jurusan": pilihjurusan_receive,
    }
    db.matakuliah.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/editmatkul/<string:id>', methods=['GET', 'POST'])
def editmatkul(id):
    
    if request.method == 'POST':
        matkul_receive = request.form['namematkul']
        pilihjurusan_receive = request.form['jurusan']

        db.matakuliah.update_one({'_id': ObjectId(id)}, {'$set': {'Nama_Matkul': matkul_receive, 'Jurusan': pilihjurusan_receive}})
        return jsonify({'result': 'success'})

    
    token_receive = request.cookies.get("mytoken")
    try:
        data = db.matakuliah.find_one({'_id': ObjectId(id)})

        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        selected_major = data.get('Jurusan')
        return render_template('admin/editmatkul.html', data=data, active_page="mnjm_matkul", user_info=user_info, selected_major=selected_major)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/deletematkul/<string:id>', methods=['POST'])
def deletematkul(id):
    db.matakuliah.delete_one({'_id': ObjectId(id)})
    return jsonify({'result': 'success'})

@app.route('/manajemen-kelas')
def mnjm_kelas():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        nip_user = user_info['username']
        matakuliah_list = db.matakuliah.find()
        kelas_list = list(db.kelas.aggregate([
            {
                "$lookup": {
                    "from": "matakuliah",
                    "localField": "Kode_Matkul",
                    "foreignField": "Kode_Matkul",
                    "as": "info_matakuliah"
                }
            },
            {
                "$unwind": "$info_matakuliah"
            },
            {
                "$match": {
                    "nip": nip_user
                }
            },
            {
                "$project": {
                    "Kode_Matkul": 1,
                    "nip": 1,
                    "Waktu": 1,
                    "Ruang": 1,
                    "Hari": 1,
                    "Nama_Matkul": "$info_matakuliah.Nama_Matkul",
                    "Jurusan": "$info_matakuliah.Jurusan"
                }
            }
        ]))
        return render_template('dosen/mnjmkelas.html', active_page="mnjm_kls" ,matakuliah_list=matakuliah_list, user_info=user_info, kelas_list=kelas_list)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/manajemen-kelas/savekelas', methods=['POST'])
def savekelas():
    matkul_receive = request.form['matkul']
    ftime_receive = request.form['ftime']
    fruang_receive = request.form['fruang']
    dosen_receive = request.form['dosen']
    day_receive = request.form['day']
    namematkul_receive = request.form['selectedNama']

    doc = {
        "Kode_Matkul": matkul_receive,
        "Nama_Matkul": namematkul_receive,
        "nip": dosen_receive,
        "Waktu": ftime_receive,
        "Ruang": fruang_receive,
        "Hari": day_receive,
    }
    db.kelas.insert_one(doc)
    return jsonify({'result': 'success'})

@app.route('/editkelas/<string:id>', methods=['GET', 'POST'])
def editkelas(id):
    if request.method == 'POST':
        time_receive = request.form['ewaktu']
        room_receive = request.form['eruang']
        day_receive = request.form['day']

        db.kelas.update_one({'_id': ObjectId(id)}, {'$set': {'Waktu': time_receive, 'Ruang': room_receive, 'Hari' : day_receive}})
        return jsonify({'result' : 'success'})
    
    token_receive = request.cookies.get("mytoken")
    try:
        data = db.kelas.find_one({'_id': ObjectId(id)})
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        selected_day = data.get('Hari')

        return render_template('dosen/editkelas.html', data=data, user_info=user_info ,active_page="mnjm_kls", selected_day=selected_day)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/deletekelas/<string:id>', methods=['POST'])
def deletekelas(id):
    db.kelas.delete_one({'_id': ObjectId(id)})
    db.kelas_mhs.delete_one({'idKelas': ObjectId(id)})
    return jsonify({"result": "success"})


@app.route('/tambah-kelas-mahasiswa/<string:id>', methods=['GET', 'POST'])
def tambahklsmhs(id):
    token_receive = request.cookies.get("mytoken")
    if request.method == 'POST':
        nim_receive = request.form['getnim']
        idKelas_recive = request.form['idKelas']
        idKelas = ObjectId(idKelas_recive)
        data = db.kelas_mhs.find_one({"nim": nim_receive, "idKelas": idKelas})
        if data:
            return jsonify({'error': True, 'message': 'Data sudah ada'})
        else:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
            user_info = db.users.find_one({'username':payload.get('id')})
            pertemuan = {f'pertemuan{i}': 'Tidak Hadir' for i in range(1, 17)}
            db.kelas_mhs.insert_one({'idKelas': idKelas, 'username' : user_info['username'], 'nim': nim_receive, **pertemuan})
            return jsonify({'success': True})

    
    token_receive = request.cookies.get("mytoken")
    try:
        data = db.kelas.find_one({'_id': ObjectId(id)})
        idc = ObjectId(id)
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        kls_mhs = list(db.kelas_mhs.aggregate([
            {
                "$lookup": {
                    "from": "users",
                    "localField": "nim",
                    "foreignField": "username",
                    "as": "info_mhs"
                }
            },
            {
                "$unwind": "$info_mhs"
            },
            {
                "$match": {
                    "idKelas": idc
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "fullname": "$info_mhs.full_name", 
                    "nim": "$info_mhs.username",
                    "id_ortu": "$info_mhs.id_ortu",
                    "fname_ortu": "$info_mhs.fname_ortu",

                }
            }
        ]))
        for kls in kls_mhs:
            kls['_id'] = str(kls['_id'])

        return render_template('dosen/tambahmhs.html', data=data, user_info=user_info,active_page="mnjm_kls",kls_mhs=kls_mhs)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/carimahasiswa', methods=['POST'])
def carimhs():
    searchValue = request.form['searchValue']
    query = {
        '$and': [
            {'role': 'mahasiswa'},
            {
                '$or': [
                    {'full_name': {'$regex': searchValue, '$options': 'i'}},
                    {'username': searchValue}
                ]
            }
        ]
    }
    hasil = list(db.users.find(query, {'_id': 0}))
    return jsonify({'hasil': hasil})

@app.route('/deletetmbhmhs/<string:id>', methods=["POST"])
def deletetmbhmhs(id):
    db.kelas_mhs.delete_one({'_id': ObjectId(id)})
    return jsonify({"result": "success"})

@app.route('/manajemen-absensi')
def mnjm_absen():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        nip_user = user_info['username']
        matakuliah_list = db.matakuliah.find()
        kelas_list = list(db.kelas.aggregate([
            {
                "$lookup": {
                    "from": "matakuliah",
                    "localField": "Kode_Matkul",
                    "foreignField": "Kode_Matkul",
                    "as": "info_matakuliah"
                }
            },
            {
                "$unwind": "$info_matakuliah"
            },
            {
                "$match": {
                    "nip": nip_user
                }
            },
            {
                "$project": {
                    "Kode_Matkul": 1,
                    "nip": 1,
                    "Waktu": 1,
                    "Ruang": 1,
                    "Nama_Matkul": "$info_matakuliah.Nama_Matkul",
                    "Jurusan": "$info_matakuliah.Jurusan"
                }
            }
        ]))
        return render_template('dosen/mnjmabsen.html', active_page="mnjm_absen" ,matakuliah_list=matakuliah_list, user_info=user_info, kelas_list=kelas_list)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/absensi-mahasiswa/<string:id>')
def absenmhs(id):
    token_receive = request.cookies.get("mytoken")
    try:
        data = db.kelas.find_one({'_id': ObjectId(id)})
        idc = ObjectId(id)
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        kls_mhs = list(db.kelas_mhs.aggregate([
            {
                "$lookup": {
                    "from": "users",
                    "localField": "nim",
                    "foreignField": "username",
                    "as": "info_mhs"
                }
            },
            {
                "$unwind": "$info_mhs"
            },
            {
                "$match": {
                    "idKelas": idc
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "fullname": "$info_mhs.full_name", 
                    "nim": "$info_mhs.username",
                    "id_ortu": "$info_mhs.id_ortu",
                    "fname_ortu": "$info_mhs.fname_ortu",
                    "pertemuan": { "$concatArrays": [ 
                        [{"status": "$pertemuan1"}], 
                        [{"status": "$pertemuan2"}], 
                        [{"status": "$pertemuan3"}], 
                        [{"status": "$pertemuan4"}], 
                        [{"status": "$pertemuan5"}], 
                        [{"status": "$pertemuan6"}], 
                        [{"status": "$pertemuan7"}], 
                        [{"status": "$pertemuan8"}], 
                        [{"status": "$pertemuan9"}], 
                        [{"status": "$pertemuan10"}], 
                        [{"status": "$pertemuan11"}], 
                        [{"status": "$pertemuan12"}], 
                        [{"status": "$pertemuan13"}], 
                        [{"status": "$pertemuan14"}], 
                        [{"status": "$pertemuan15"}], 
                        [{"status": "$pertemuan16"}] 
                    ]} 
                }
            }
        ]))
        return render_template('dosen/absensimhs.html', active_page="mnjm_absen", user_info=user_info, data=data, kls_mhs=kls_mhs, id=id)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/update_status', methods=['POST'])
def update_status():
    nomer_induk = request.form['nim']
    idabsensi = request.form['idabsensi']
    pertemuan = request.form['pertemuan']
    status = request.form['status']

    db.kelas_mhs.update_one(
        {'nim': nomer_induk, 'idKelas' : ObjectId(idabsensi)},
        {'$set': {f'pertemuan{pertemuan}': status}}
    )

    return 'Success', 200

@app.route('/Acoount')
def account():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]},)
        return render_template('account.html', active_page='account', user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/update_profile", methods=["POST"])
def save_img():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload["id"]
        name_receive = request.form["name_give"]
        date_receive = request.form["date_give"]
        new_doc = {"full_name": name_receive, "tanggal_lahir": date_receive}
        if "file_give" in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"myassets/profile/{username}.{extension}"
            file.save("./static/" + file_path)
            new_doc["profile_pic"] = filename
            new_doc["profile_pic_real"] = file_path
        db.users.update_one({"username": payload["id"]}, {"$set": new_doc})
        return jsonify({"result": "success", "msg": "Profile updated!"})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/changepassword', methods=['GET','POST'])
def changepassword():
    token_receive = request.cookies.get("mytoken")
    if request.method == 'POST':
        oldpw = request.form["old_password"]
        newpw = request.form["new_password"]
        oldpw_hash = hashlib.sha256(oldpw.encode("utf-8")).hexdigest()
        newpw_hash = hashlib.sha256(newpw.encode("utf-8")).hexdigest()

        result = db.users.find_one(
            {
                "password": oldpw_hash,
            }
        )

        if result:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])

            db.users.update_one({"username": payload["id"]}, {'$set': {'password': newpw_hash}})
            return jsonify(
                {
                    "result": "success",
                }
            )  
        else:
            return jsonify(
                {
                    "result": "fail",
                }
            )
        pass
    
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template('changepw.html', active_page='changepw', user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/mahasiswa-absensi')
def mhsabsensi():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        nim_user = user_info['username']
        pipeline = [
                    {"$match": {"nim": nim_user}},
                    {"$lookup": {
                        "from": "kelas",
                        "localField": "idKelas",
                        "foreignField": "_id",
                        "as": "kelas"
                    }},
                    {"$lookup": {
                        "from": "users",
                        "localField": "username",
                        "foreignField": "username",
                        "as": "user"
                    }},
                    {"$project": {
                        "_id": 1,
                        "nim" : 1,
                        "kode_matkul": "$kelas.Kode_Matkul",
                        "nama_matkul": "$kelas.Nama_Matkul",
                        "waktu": "$kelas.Waktu",
                        "ruang": "$kelas.Ruang",
                        "dosen": "$user.full_name"
                    }}
        ]
        data = list(db.kelas_mhs.aggregate(pipeline))

        return render_template("mahasiswa/daftarmatkul.html", active_page='matkul_mhs', user_info=user_info, data=data)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/view-kelas-mahasiswa/<string:id>')
def viewabsenmhs(id):
    token_receive = request.cookies.get("mytoken")
    try:
        data = db.kelas.find_one({'_id': ObjectId(id)})
        idc = ObjectId(id)
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        kls_mhs = list(db.kelas_mhs.aggregate([
            {
                "$lookup": {
                    "from": "users",
                    "localField": "nim",
                    "foreignField": "username",
                    "as": "info_mhs"
                }
            },
            {
                "$unwind": "$info_mhs"
            },
            {
                "$match": {
                    "_id": idc
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "fullname": "$info_mhs.full_name", 
                    "nim": "$info_mhs.username",
                    "id_ortu": "$info_mhs.id_ortu",
                    "fname_ortu": "$info_mhs.fname_ortu",
                    "pertemuan": { "$concatArrays": [ 
                        [{"status": "$pertemuan1"}], 
                        [{"status": "$pertemuan2"}], 
                        [{"status": "$pertemuan3"}], 
                        [{"status": "$pertemuan4"}], 
                        [{"status": "$pertemuan5"}], 
                        [{"status": "$pertemuan6"}], 
                        [{"status": "$pertemuan7"}], 
                        [{"status": "$pertemuan8"}], 
                        [{"status": "$pertemuan9"}], 
                        [{"status": "$pertemuan10"}], 
                        [{"status": "$pertemuan11"}], 
                        [{"status": "$pertemuan12"}], 
                        [{"status": "$pertemuan13"}], 
                        [{"status": "$pertemuan14"}], 
                        [{"status": "$pertemuan15"}], 
                        [{"status": "$pertemuan16"}] 
                    ]} 
                }
            }
        ]))
        return render_template('mahasiswa/absensimhs.html', active_page="mnjm_absen", user_info=user_info, data=data, kls_mhs=kls_mhs, id=id)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/mahasiswa-absensi-ortu')
def mhsabsensiortu():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        nim_user = user_info['username']
        nim_user = nim_user.replace("01", "", 1)
        
        pipeline = [
                    {"$match": {"nim": nim_user}},
                    {"$lookup": {
                        "from": "kelas",
                        "localField": "idKelas",
                        "foreignField": "_id",
                        "as": "kelas"
                    }},
                    {"$lookup": {
                        "from": "users",
                        "localField": "username",
                        "foreignField": "username",
                        "as": "user"
                    }},
                    {"$project": {
                        "_id": 1,
                        "nim" : 1,
                        "kode_matkul": "$kelas.Kode_Matkul",
                        "nama_matkul": "$kelas.Nama_Matkul",
                        "waktu": "$kelas.Waktu",
                        "ruang": "$kelas.Ruang",
                        "dosen": "$user.full_name"
                    }}
        ]
        data = list(db.kelas_mhs.aggregate(pipeline))

        return render_template("orangtua/daftarmatkul.html", active_page='matkul_mhs', user_info=user_info, data=data)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/view-kelas-mahasiswa-ortu/<string:id>')
def viewabsenmhsortu(id):
    token_receive = request.cookies.get("mytoken")
    try:
        data = db.kelas.find_one({'_id': ObjectId(id)})
        idc = ObjectId(id)
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        kls_mhs = list(db.kelas_mhs.aggregate([
            {
                "$lookup": {
                    "from": "users",
                    "localField": "nim",
                    "foreignField": "username",
                    "as": "info_mhs"
                }
            },
            {
                "$unwind": "$info_mhs"
            },
            {
                "$match": {
                    "_id": idc
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "fullname": "$info_mhs.full_name", 
                    "nim": "$info_mhs.username",
                    "id_ortu": "$info_mhs.id_ortu",
                    "fname_ortu": "$info_mhs.fname_ortu",
                    "pertemuan": { "$concatArrays": [ 
                        [{"status": "$pertemuan1"}], 
                        [{"status": "$pertemuan2"}], 
                        [{"status": "$pertemuan3"}], 
                        [{"status": "$pertemuan4"}], 
                        [{"status": "$pertemuan5"}], 
                        [{"status": "$pertemuan6"}], 
                        [{"status": "$pertemuan7"}], 
                        [{"status": "$pertemuan8"}], 
                        [{"status": "$pertemuan9"}], 
                        [{"status": "$pertemuan10"}], 
                        [{"status": "$pertemuan11"}], 
                        [{"status": "$pertemuan12"}], 
                        [{"status": "$pertemuan13"}], 
                        [{"status": "$pertemuan14"}], 
                        [{"status": "$pertemuan15"}], 
                        [{"status": "$pertemuan16"}] 
                    ]} 
                }
            }
        ]))
        return render_template('orangtua/absensimhs.html', active_page="mnjm_absen", user_info=user_info, data=data, kls_mhs=kls_mhs, id=id)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/laporan-mahasiswa')
def lpmhs():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        username = payload["id"]
        pipeline = [
            {"$match": {"sender": username, "type": "sender"}},
            {"$lookup": {
                "from": "users",
                "localField": "receiver",
                "foreignField": "username",
                "as": "myuser"
            }},
            {"$unwind": "$myuser"},
            {"$project": {"profile_pic_real": "$myuser.profile_pic_real", "_id": 0, "message":1, "receiver" : 1, "fullname":'$myuser.full_name'}}
        ]
        result = list(db.messages.aggregate(pipeline))
        return render_template("dosen/laporanmhs.html", active_page="laporan_mhs", active_page1="lpsent",user_info=user_info, messages=result)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))   

@app.route('/laporan-mahasiswa-recive')
def lpmhsrecive():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        username = payload["id"]
        pipeline = [
            {"$match": {"receiver": username}},
            {"$lookup": {
                "from": "users",
                "localField": "sender",
                "foreignField": "username",
                "as": "myuser"
            }},
            {"$unwind": "$myuser"},
            {"$project": {"profile_pic_real": "$myuser.profile_pic_real", "_id": 0, "message":1, "sender" : 1}}
        ]
        result = list(db.messages.aggregate(pipeline))
        return render_template("dosen/laporanmhsrecive.html", active_page="laporan_mhs", active_page1="lpinbox", user_info=user_info, messages=result)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))   

@app.route('/laporan-mahasiswa-ortu')
def lpmhsortu():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        username = payload["id"]
        twenty_four_hours_ago = datetime.now() - timedelta(days=1)
        pipeline = [
            {"$match": {"sender": username, "type": "sender"}},
            {"$lookup": {
                "from": "users",
                "localField": "receiver",
                "foreignField": "username",
                "as": "myuser"
            }},
            {"$unwind": "$myuser"},
            {"$project": {
                "profile_pic_real": "$myuser.profile_pic_real", 
                "_id": 0, 
                "message":1, 
                "receiver" : 1, 
                "fullname":'$myuser.full_name',
                "tanggal": {
                    "$cond": [
                        {"$lt": [{"$dateFromString": {"dateString": "$tanggal", "format": "%d/%m/%Y %H:%M:%S"}}, twenty_four_hours_ago]},
                        {"$dateToString": {"format": "%d/%m/%Y", "date": {"$dateFromString": {"dateString": "$tanggal", "format": "%d/%m/%Y %H:%M:%S"}}}},
                        {"$dateToString": {"format": "%H:%M", "date": {"$dateFromString": {"dateString": "$tanggal", "format": "%d/%m/%Y %H:%M:%S"}}}}
                    ]
                }
            }}
        ]
        
        result = list(db.messages.aggregate(pipeline))
        return render_template("orangtua/laporanmhs.html", active_page="laporan_mhs", active_page1="lpsent",user_info=user_info, messages=result)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))   

@app.route('/laporan-mahasiswa-recive-ortu')
def lpmhsreciveortu():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({'username':payload.get('id')})
        username = payload["id"]
        pipeline = [
            {"$match": {"receiver": username}},
            {"$lookup": {
                "from": "users",
                "localField": "sender",
                "foreignField": "username",
                "as": "myuser"
            }},
            {"$unwind": "$myuser"},
            {"$project": {"profile_pic_real": "$myuser.profile_pic_real", "_id": 0, "message":1, "sender" : 1}}
        ]
        result = list(db.messages.aggregate(pipeline))
        return render_template("orangtua/laporanmhsrecive.html", active_page="laporan_mhs", active_page1="lpinbox", user_info=user_info, messages=result)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))   

@app.route('/send_message', methods=['POST'])
def send_message():

    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload["id"]
        receiver = request.form["to"]
        message = request.form["pesan"]
        type = "sender"

        users = db.users
        if not users.find_one({"username": username}):
            return "Pengirim tidak ditemukan"
        if not users.find_one({"username": receiver}):
            return "Penerima tidak ditemukan"
        dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        messages = db.messages
        messages.insert_one({"sender": username, "receiver": receiver, "message": message, "type": type, "tanggal" : dt_string})
        return jsonify({"result": "success"})

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


def get_user_role():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.users.find_one({"username": payload["id"]})
        role = user_info.get('role')
        return role
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.context_processor
def inject_role():
    return {'user_role': get_user_role()}

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)