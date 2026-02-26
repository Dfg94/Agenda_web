from flask import Flask,render_template,request,jsonify,send_from_directory,session,redirect,url_for
import json,os
from datetime import datetime,timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message

app=Flask(__name__)
app.secret_key="agenda_girlsdate_secreta_123"
serializer = URLSafeTimedSerializer(app.secret_key)

# Configuración de correo
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)

@app.route('/sw.js')
def service_worker():
    return send_from_directory(app.static_folder,'sw.js',mimetype='application/javascript')

if os.path.exists("/data"):
    archivo = "/data/datos.json"
    archivo_usuarios = "/data/usuarios.json"
else:
    archivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos.json")
    archivo_usuarios = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usuarios.json")

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

def cargar_usuarios():
    if not os.path.exists(archivo_usuarios):
        return []
    return json.load(open(archivo_usuarios))

def guardar_usuarios(data):
    json.dump(data, open(archivo_usuarios, "w"), indent=4)

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
    cliente_nombre = session.get("cliente_nombre")
    cliente_email = session.get("cliente_email")
    return render_template("index.html",servicios=servicios,dias_extras=dias_extras, cliente_nombre=cliente_nombre, cliente_email=cliente_email)

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
    # Solo permitir reservas si hay sesión iniciada de un cliente
    cliente_email = session.get("cliente_email")
    if not cliente_email:
        return "No autorizado - Inicia sesión primero", 401

    data=cargar()
    nueva_reserva = request.json
    nueva_reserva["email"] = cliente_email # Forzar que la reserva tenga el email del usuario
    data["reservas"].append(nueva_reserva)
    guardar(data)
    return "ok"

@app.route("/registro", methods=["GET", "POST"])
def registro():
    error = None
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = request.form.get("password")
        
        usuarios = cargar_usuarios()
        
        # Verificar si el email ya existe
        if any(u["email"] == email for u in usuarios):
            error = "Este correo ya está registrado."
        elif not nombre or not email or not password:
            error = "Todos los campos son obligatorios."
        else:
            nuevo_usuario = {
                "nombre": nombre,
                "email": email,
                "password": generate_password_hash(password)
            }
            usuarios.append(nuevo_usuario)
            guardar_usuarios(usuarios)
            
            # Iniciar sesión automáticamente al registrarse
            session["cliente_email"] = email
            session["cliente_nombre"] = nombre
            return redirect(url_for("home"))
            
    return render_template("registro.html", error=error)

@app.route("/login_cliente", methods=["GET", "POST"])
def login_cliente():
    error = None
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        usuarios = cargar_usuarios()
        usuario_encontrado = next((u for u in usuarios if u["email"] == email), None)
        
        if usuario_encontrado and check_password_hash(usuario_encontrado["password"], password):
            session["cliente_email"] = usuario_encontrado["email"]
            session["cliente_nombre"] = usuario_encontrado["nombre"]
            return redirect(url_for("home"))
        else:
            error = "Correo o contraseña incorrectos"
            
    return render_template("login_cliente.html", error=error)

@app.route("/logout_cliente")
def logout_cliente():
    session.pop("cliente_email", None)
    session.pop("cliente_nombre", None)
    return redirect(url_for("home"))

@app.route("/recuperar_password", methods=["GET", "POST"])
def recuperar_password():
    error = None
    mensaje = None
    if request.method == "POST":
        email = request.form.get("email")
        usuarios = cargar_usuarios()
        usuario = next((u for u in usuarios if u["email"] == email), None)
        
        if usuario:
            # Generar token seguro que expira
            token = serializer.dumps(email, salt="recuperar-password")
            link = url_for("resetear_password", token=token, _external=True)
            
            try:
                # Intentar enviar el correo
                msg = Message('Recuperación de Contraseña - Agenda Beauty',
                              sender=app.config['MAIL_USERNAME'],
                              recipients=[email])
                
                msg.body = f'''Hola {usuario["nombre"]},

Para restablecer tu contraseña, haz clic en el siguiente enlace:
{link}

Si no solicitaste este cambio, simplemente ignora este correo.
El enlace expirará en 1 hora.

Saludos,
El equipo de Agenda Beauty.
'''
                mail.send(msg)
                mensaje = "Si el correo está registrado y configuramos todo bien, recibirás un enlace."
            except Exception as e:
                # Si falla (ej. credenciales inválidas), mostrar error en consola pero no romper la app
                print(f"Error al enviar correo: {e}")
                error = "Hubo un problema al intentar enviar el correo. Por favor, contacta al administrador."
                
        else:
            # Mensaje genérico por seguridad
            mensaje = "Si el correo está registrado, recibirás un enlace para recuperar tu contraseña."
            
    return render_template("recuperar_password.html", error=error, mensaje=mensaje)

@app.route("/resetear_password/<token>", methods=["GET", "POST"])
def resetear_password(token):
    error = None
    try:
        # El token expira en 1 hora (3600 segundos)
        email = serializer.loads(token, salt="recuperar-password", max_age=3600)
    except:
        return render_template("resetear_password.html", error="El enlace de recuperación es inválido o ha expirado.")

    if request.method == "POST":
        password = request.form.get("password")
        usuarios = cargar_usuarios()
        
        for u in usuarios:
            if u["email"] == email:
                u["password"] = generate_password_hash(password)
                guardar_usuarios(usuarios)
                # Iniciar sesión automáticamente
                session["cliente_email"] = u["email"]
                session["cliente_nombre"] = u["nombre"]
                return redirect(url_for("home"))
                
        error = "Usuario no encontrado."

    return render_template("resetear_password.html", error=error)

@app.route("/mis_turnos")
def mis_turnos():
    cliente_email = session.get("cliente_email")
    if not cliente_email:
        return redirect(url_for("login_cliente"))

    d = cargar()
    mis_reservas = [r for r in d["reservas"] if r.get("email") == cliente_email]

    ahora = datetime.now()
    proximos = []
    historial = []

    for r in mis_reservas:
        fecha_hora_str = f"{r['fecha']} {r['inicio']}"
        fecha_hora_obj = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M")

        if fecha_hora_obj >= ahora:
            proximos.append(r)
        else:
            historial.append(r)

    # Ordenar próximos del más cercano al más lejano
    proximos.sort(key=lambda x: datetime.strptime(f"{x['fecha']} {x['inicio']}", "%Y-%m-%d %H:%M"))
    
    # Ordenar historial del más reciente al más antiguo
    historial.sort(key=lambda x: datetime.strptime(f"{x['fecha']} {x['inicio']}", "%Y-%m-%d %H:%M"), reverse=True)

    return render_template("mis_turnos.html", proximos=proximos, historial=historial, cliente_nombre=session.get("cliente_nombre"))

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
