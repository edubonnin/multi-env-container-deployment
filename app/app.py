from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import psycopg2
import redis
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Configuración desde variables de entorno
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'appdb')
DB_USER = os.getenv('DB_USER', 'user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')

REDIS_HOST = os.getenv('REDIS_HOST', None)
REDIS_PORT = os.getenv('REDIS_PORT', '6379')
REDIS_MESSAGE_KEY = os.getenv('REDIS_MESSAGE_KEY', 'app:message')

ENV = os.getenv('ENV', 'dev')

# Verifica conexión con Postgres
def check_database():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=3
        )
        conn.close()
        return {
            'status': 'connected',
            'message': 'PostgreSQL conectado correctamente',
            'healthy': True
        }
    except Exception as e:
        return {
            'status': 'disconnected',
            'message': f'Error: {str(e)}',
            'healthy': False
        }

# Verifica conexión con Redis
def check_redis():
    if not REDIS_HOST or ENV == 'dev':
        return {
            'status': 'not_configured',
            'message': 'Redis no configurado en este entorno',
            'healthy': True
        }
    
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=int(REDIS_PORT),
            socket_connect_timeout=3
        )
        r.ping()
        return {
            'status': 'connected',
            'message': 'Redis conectado correctamente',
            'healthy': True
        }
    except Exception as e:
        return {
            'status': 'disconnected',
            'message': f'Error: {str(e)}',
            'healthy': False
        }

# Inicializa la base de datos con una tabla de ejemplo"""
def init_database():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        # Crear tabla si no existe
        cur.execute("""
            CREATE TABLE IF NOT EXISTS health_logs (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP,
                status VARCHAR(50)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS cars (
                id SERIAL PRIMARY KEY,
                brand VARCHAR(100) NOT NULL,
                model VARCHAR(100) NOT NULL,
                year INTEGER NOT NULL CHECK (year >= 1886),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_cars_brand_model_year
            ON cars (brand, model, year)
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error inicializando base de datos: {e}")
        return False

# Registra el healthcheck en la base de datos"""
def log_health_check():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO health_logs (timestamp, status) VALUES (%s, %s)",
            (datetime.now(), 'healthy')
        )
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error logging health check: {e}")

def get_cached_data():
    """Ejemplo de uso de caché con Redis"""
    if not REDIS_HOST or ENV == 'dev':
        return None
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT))
        
        # Intentar obtener datos de caché
        cached = r.get('health_count')
        
        if cached:
            count = int(cached)
        else:
            # Simular consulta a BD
            count = 1
        
        # Incrementar y guardar en caché
        count += 1
        r.setex('health_count', 300, count)  # 5 minutos de TTL
        
        return count
    except Exception as e:
        print(f"Error usando Redis: {e}")
        return None

# Recupera la lista de coches registrados
def get_cars():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, brand, model, year, created_at
            FROM cars
            ORDER BY created_at DESC, id DESC
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        cars = [
            {
                'id': row[0],
                'brand': row[1],
                'model': row[2],
                'year': row[3],
                'created_at': row[4]
            }
            for row in rows
        ]
        return cars, None
    except Exception as e:
        return [], str(e)

# Inserta un coche en la base de datos
def create_car(brand, model, year):
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO cars (brand, model, year)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (brand, model, year)
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return new_id, None
    except Exception as e:
        if conn:
            conn.rollback()
        return None, str(e)
    finally:
        if conn:
            conn.close()

# Obtención del mensaje almacenado en redis
def get_redis_message():
    if not REDIS_HOST or ENV == 'dev':
        return None, None

    try:
        r = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), decode_responses=True)
        message = r.get(REDIS_MESSAGE_KEY)
        return message, None
    except Exception as e:
        return None, str(e)

# Eliminación de coche por ID
def delete_car(car_id):
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        cur.execute("DELETE FROM cars WHERE id = %s", (car_id,))
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        if deleted:
            return True, None
        return False, 'Registro no encontrado'
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)
    finally:
        if conn:
            conn.close()

# Endpoint raíz -> Página principal
@app.route('/')
def index():
    db_status = check_database()
    redis_status = check_redis()
    cars = []
    cars_error = None
    redis_message = None
    redis_message_error = None

    if db_status['healthy']:
        cars, cars_error = get_cars()
    else:
        cars_error = 'Base de datos no disponible'

    if redis_status['healthy'] and redis_status['status'] == 'connected':
        redis_message, redis_message_error = get_redis_message()
    elif redis_status['status'] == 'disconnected':
        redis_message_error = redis_status['message']
    
    return render_template(
        'index.html',
        db_status=db_status,
        redis_status=redis_status,
        env=ENV,
        cars=cars,
        cars_error=cars_error,
        redis_message=redis_message,
        redis_message_error=redis_message_error,
        redis_message_key=REDIS_MESSAGE_KEY
    )

# Formulario para añadir coches
@app.route('/cars', methods=['POST'])
def add_car():
    brand = request.form.get('brand', '').strip()
    model = request.form.get('model', '').strip()
    year_raw = request.form.get('year', '').strip()

    if not brand or not model or not year_raw:
        flash('Todos los campos son obligatorios.', 'error')
        return redirect(url_for('index'))

    try:
        year = int(year_raw)
    except ValueError:
        flash('El año debe ser un número entero.', 'error')
        return redirect(url_for('index'))

    current_year = datetime.now().year
    if year < 1886 or year > current_year:
        flash(f'El año debe estar entre 1886 y {current_year}.', 'error')
        return redirect(url_for('index'))

    _, error = create_car(brand, model, year)
    if error:
        flash(f'No se pudo registrar el coche: {error}', 'error')
    else:
        flash('Coche añadido correctamente.', 'success')

    return redirect(url_for('index'))

# Eliminación de coches
@app.route('/cars/<int:car_id>/delete', methods=['POST'])
def remove_car(car_id):
    success, error = delete_car(car_id)
    if success:
        flash('Coche eliminado correctamente.', 'success')
    else:
        flash(f'No se pudo eliminar el coche: {error}', 'error')
    return redirect(url_for('index'))

# Registro de dos endpoints para healthcheck
@app.route('/status')
@app.route('/health')
def health():
    db_status = check_database()
    redis_status = check_redis()
    
    # Log del healthcheck en BD
    if db_status['healthy']:
        log_health_check()
    
    # Obtener contador de caché si está disponible
    cache_count = get_cached_data()
    cars_count = None
    redis_message = None
    if db_status['healthy']:
        cars, error = get_cars()
        if not error:
            cars_count = len(cars)
    if redis_status['healthy'] and redis_status['status'] == 'connected':
        redis_message, _ = get_redis_message()
    
    overall_healthy = db_status['healthy'] and redis_status['healthy']
    
    response = {
        'status': 'healthy' if overall_healthy else 'unhealthy',
        'timestamp': datetime.now().isoformat(),
        'environment': ENV,
        'services': {
            'database': db_status,
            'cache': redis_status
        }
    }
    
    if cache_count:
        response['cache_requests'] = cache_count
    if cars_count is not None:
        response['data'] = {
            'cars_count': cars_count
        }
    if redis_message:
        response.setdefault('data', {})['redis_message'] = redis_message
    
    status_code = 200 if overall_healthy else 503
    return jsonify(response), status_code

# Endpoint para testear persistencia
@app.route('/db-test')
def db_test():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cur = conn.cursor()
        
        # Insertar un registro de prueba
        cur.execute(
            "INSERT INTO health_logs (timestamp, status) VALUES (%s, %s) RETURNING id",
            (datetime.now(), 'test')
        )
        new_id = cur.fetchone()[0]
        
        # Obtener todos los registros
        cur.execute("SELECT COUNT(*) FROM health_logs")
        count = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Registro creado con ID: {new_id}',
            'total_records': count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Inicializar BD al arrancar
    print("Inicializando base de datos...")
    if init_database():
        print("Base de datos inicializada correctamente")
    else:
        print("Error inicializando base de datos")
    
    # Iniciar aplicación
    app.run(host='0.0.0.0', port=5000, debug=(ENV == 'dev'))
