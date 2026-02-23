from flask import Flask,render_template,request,jsonify,send_from_directory,session,redirect,url_for
import json,os
from datetime import datetime,timedelta

app=Flask(__name__)
app.secret_key="agenda_girlsdate_secreta_123"

@app.route('/sw.js')
def service_worker():
    return send_from_directory(app.static_folder,'sw.js',mimetype='application/javascript')

if os.path.exists("/data"):
    archivo = "/data/datos.json"
else:
    archivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos.json")

servicios={
"semi-permanente":60,
"semi-permanentes refuerzo":90,
"extension S-M":90,
"extension L-XL":120,
"relleno S-M":90,
"relleno L-XL":120,
"belleza pies":30,
"pies + semi":50,
"pedicura spa":45,
"spa + semi":60,
"retiro semi":20,
"retiro uñas":30,
"arreglo":15
}

def cargar():
    if not os.path.exists(archivo):
        return {"reservas":[],"extras":[],"bloqueados":[],"dias_bloqueados":[]}
    return json.load(open(archivo))

def guardar(data):
    json.dump(data,open(archivo,"w"),indent=4)


def generar_bloque(base,reservas,limite):

    if not reservas:
        return base

    reservas.sort(key=lambda r:r["inicio"])

    horas=[]

    primer_inicio=datetime.strptime(reservas[0]["inicio"],"%H:%M")

    for h in base:
        h_dt=datetime.strptime(h,"%H:%M")
        if h_dt < primer_inicio:
            horas.append(h)

    ultima=reservas[-1]
    inicio=datetime.strptime(ultima["inicio"],"%H:%M")
    dur=servicios[ultima["servicio"]]
    fin=inicio+timedelta(minutes=dur)

    while fin <= limite:
        horas.append(fin.strftime("%H:%M"))
        fin += timedelta(minutes=90)

    return horas


def generar_horas(fecha):

    data=cargar()

    if fecha in data["dias_bloqueados"]:
        return []

    reservas=[r for r in data["reservas"] if r["fecha"]==fecha]

    mañana=[]
    tarde=[]

    for r in reservas:
        hora=datetime.strptime(r["inicio"],"%H:%M")
        if hora.hour < 14:
            mañana.append(r)
        else:
            tarde.append(r)

    base_m=["09:00","10:30","12:00"]
    base_t=["15:30","17:00","18:30"]

    limite_m=datetime.strptime("12:00","%H:%M")
    limite_t=datetime.strptime("18:30","%H:%M")

    horas=[]
    
    # Solo agregar bloques base normales de Lunes a Viernes (0 a 4)
    # 5 y 6 son Sábado y Domingo, que solo funcionarán a base de "extras"
    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    if fecha_dt.weekday() < 5:
        horas+=generar_bloque(base_m,mañana,limite_m)
        horas+=generar_bloque(base_t,tarde,limite_t)

    for e in data["extras"]:
        if e["fecha"]==fecha:
            horas.append(e["hora"])

    hoy_str = datetime.now().strftime("%Y-%m-%d")
    ahora = datetime.now()

    horas_filtro_tiempo = []
    for h in horas:
        if fecha == hoy_str:
            h_dt = datetime.strptime(h, "%H:%M")
            if h_dt.time() <= ahora.time():
                continue
        horas_filtro_tiempo.append(h)

    horas=[h for h in horas_filtro_tiempo if not any(
        b["fecha"]==fecha and b["hora"]==h
        for b in data["bloqueados"]
    )]

    return sorted(set(horas))


@app.route("/")
def home():
    d=cargar()
    dias_extras=list(set([e["fecha"] for e in d.get("extras",[])]))
    return render_template("index.html",servicios=servicios,dias_extras=dias_extras)


@app.route("/horarios")
def horarios():
    return jsonify(generar_horas(request.args.get("fecha")))


@app.route("/reservas")
def reservas():
    data=cargar()
    f=request.args.get("fecha")
    return jsonify([r for r in data["reservas"] if r["fecha"]==f])


@app.route("/crear",methods=["POST"])
def crear():
    data=cargar()
    data["reservas"].append(request.json)
    guardar(data)
    return "ok"


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("usuario") == "carlarodriguez" and request.form.get("clave") == "violeta":
            session["admin_logueado"] = True
            return redirect(url_for("admin"))
        else:
            error = "Usuario o contraseña incorrectos"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.pop("admin_logueado", None)
    return redirect(url_for("login"))


@app.route("/admin")
def admin():
    if not session.get("admin_logueado"):
        return redirect(url_for("login"))
        
    d=cargar()
    return render_template("admin.html",
        servicios=servicios,
        reservas=d["reservas"],
        extras=d["extras"],
        bloqueados=d["bloqueados"],
        dias_bloqueados=d["dias_bloqueados"]
    )


@app.route("/eliminar",methods=["POST"])
def eliminar():
    d=cargar()
    d["reservas"].pop(request.json["index"])
    guardar(d)
    return "ok"


@app.route("/agregar_extra",methods=["POST"])
def extra():
    d=cargar()
    d["extras"].append(request.json)
    guardar(d)
    return "ok"


@app.route("/borrar_extra",methods=["POST"])
def borrar_extra():
    d=cargar()
    d["extras"].pop(request.json["index"])
    guardar(d)
    return "ok"


@app.route("/bloquear",methods=["POST"])
def bloquear():
    d=cargar()
    d["bloqueados"].append(request.json)
    guardar(d)
    return "ok"


@app.route("/desbloquear",methods=["POST"])
def desbloquear():
    d=cargar()
    d["bloqueados"].pop(request.json["index"])
    guardar(d)
    return "ok"


@app.route("/bloquear_dia",methods=["POST"])
def bloquear_dia():
    d=cargar()
    d["dias_bloqueados"].append(request.json["fecha"])
    guardar(d)
    return "ok"


@app.route("/desbloquear_dia",methods=["POST"])
def desbloquear_dia():
    d=cargar()
    d["dias_bloqueados"].pop(request.json["index"])
    guardar(d)
    return "ok"


if __name__=='__main__':
    port=int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0',port=port,debug=True)
