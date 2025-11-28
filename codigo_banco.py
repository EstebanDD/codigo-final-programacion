# -*- coding: utf-8 -*-
import sqlite3
from abc import ABC, abstractmethod
from datetime import date, timedelta, datetime

# Nombre del archivo donde se guardarán los datos
RUTA_BD = "banco_poo.sqlite"

# --- SECCIÓN: BASE DE DATOS ---

def conectar_bd():
    """
    Crea la conexión con la base de datos SQLite.
    - detect_types: Permite que Python entienda automáticamente las fechas.
    - row_factory: Permite acceder a las columnas por nombre (ej: fila['saldo']).
    """
    conn = sqlite3.connect(RUTA_BD, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_bd():
    """
    Crea las tablas necesarias si no existen.
    Se ejecuta automáticamente al iniciar el programa.
    """
    conexion = conectar_bd()
    cursor = conexion.cursor()

    # Tabla Clientes: Ahora incluye estado 'activo' para bajas lógicas (Soft Delete)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        apellido TEXT NOT NULL,
        dni TEXT NOT NULL UNIQUE,
        email TEXT,
        activo INTEGER DEFAULT 1  -- 1 = Activo, 0 = Dado de baja
    );
    """)
    
    # Tabla Cuentas: Incluye 'categoria' (Persona/Empresa) para diferenciar mantenimiento
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cuentas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT NOT NULL UNIQUE,
        saldo REAL NOT NULL,
        tipo_cuenta TEXT NOT NULL, -- CA (Caja Ahorro) o CC (Cta Corriente)
        categoria TEXT NOT NULL,   -- Persona o Empresa
        id_cliente INTEGER NOT NULL,
        limite_descubierto REAL,
        costo_mantenimiento REAL,
        fecha_creacion DATE,
        FOREIGN KEY (id_cliente) REFERENCES clientes(id)
    );
    """)
    
    # Tabla Plazos Fijos: Gestiona las inversiones como producto separado
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plazos_fijos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cuenta INTEGER NOT NULL,
        monto_inicial REAL NOT NULL,
        dias INTEGER NOT NULL,
        tasa_interes REAL NOT NULL,
        monto_final REAL NOT NULL,
        fecha_creacion DATE NOT NULL,
        fecha_vencimiento DATE NOT NULL,
        estado TEXT NOT NULL, -- 'ACTIVO' o 'COBRADO'
        FOREIGN KEY (id_cuenta) REFERENCES cuentas(id)
    );
    """)

    # Tabla Movimientos: Historial de operaciones
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cuenta INTEGER NOT NULL,
        fecha TIMESTAMP NOT NULL,
        monto REAL NOT NULL,
        tipo TEXT NOT NULL,
        descripcion TEXT,
        nro_cuenta_origen TEXT,
        nro_cuenta_destino TEXT,
        FOREIGN KEY (id_cuenta) REFERENCES cuentas(id)
    );
    """)
    
    # Tabla Parametros: Configuración global del banco (tasas, comisiones)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parametros(
        id INTEGER PRIMARY KEY CHECK (id = 1),
        comision_transferencia REAL,
        tasa_anual_pf REAL,
        costo_mantenimiento_cc REAL,
        limite_descubierto_cc REAL,
        ultimo_nro_cuenta INTEGER
    );
    """)
    
    # Insertar valores por defecto solo si la tabla está vacía
    cursor.execute("""
    INSERT INTO parametros(id, comision_transferencia, tasa_anual_pf, costo_mantenimiento_cc, limite_descubierto_cc, ultimo_nro_cuenta)
    VALUES (1, 50.0, 0.45, 100.0, 10000, 0)
    ON CONFLICT(id) DO NOTHING;
    """)
    
    conexion.commit()
    conexion.close()

# --- SECCIÓN: CLASES DE NEGOCIO (Active Record) ---

class Cliente:
    def __init__(self, nombre, apellido, dni, email="", activo=1, id_bd=None):
        self.nombre = nombre
        self.apellido = apellido
        self.dni = dni
        self.email = email
        self.activo = activo
        self.id_bd = id_bd 

    def guardar(self):
        """Guarda o actualiza al cliente en la BD."""
        conexion = conectar_bd()
        try:
            cursor = conexion.execute("""
                INSERT INTO clientes (nombre, apellido, dni, email, activo) 
                VALUES (?, ?, ?, ?, ?)""", 
                (self.nombre, self.apellido, self.dni, self.email, 1))
            conexion.commit()
            self.id_bd = cursor.lastrowid
            return True
        except sqlite3.IntegrityError:
            # Si el DNI ya existe, no creamos duplicado.
            # Recuperamos el ID existente para trabajar con él.
            conexion.close()
            existente = Cliente.buscar_por_dni(self.dni)
            if existente:
                self.id_bd = existente.id_bd
                self.nombre = existente.nombre
                self.apellido = existente.apellido
                self.activo = existente.activo
            return False 
        finally:
            if conexion: conexion.close()

    def dar_de_baja(self):
        """Baja lógica: Pone activo = 0."""
        if self.id_bd:
            conexion = conectar_bd()
            try:
                conexion.execute("UPDATE clientes SET activo = 0 WHERE id = ?", (self.id_bd,))
                conexion.commit()
                self.activo = 0
                return True
            except: return False
            finally: conexion.close()
        return False

    def reactivar(self):
        """Reactiva al cliente y resetea saldos a 0 por seguridad."""
        if self.id_bd:
            conexion = conectar_bd()
            try:
                conexion.execute("UPDATE clientes SET activo = 1 WHERE id = ?", (self.id_bd,))
                conexion.execute("UPDATE cuentas SET saldo = 0 WHERE id_cliente = ?", (self.id_bd,))
                conexion.commit()
                self.activo = 1
                return True
            except: return False
            finally: conexion.close()
        return False

    @staticmethod
    def buscar_por_dni(dni):
        """Busca un cliente por DNI y devuelve el objeto."""
        conexion = conectar_bd()
        fila = conexion.execute("SELECT * FROM clientes WHERE dni = ?", (dni,)).fetchone()
        conexion.close()
        if fila:
            c = Cliente(fila['nombre'], fila['apellido'], fila['dni'], fila['email'], fila['activo'])
            c.id_bd = fila['id']
            return c
        return None

class Movimientos:
    def __init__(self, monto, tipo, id_cuenta_bd, descripcion=None, cta_origen=None, cta_destino=None, fecha=None, id_bd=None):
        self.id_bd = id_bd
        self.id_cuenta_bd = id_cuenta_bd
        self.fecha = fecha if fecha else datetime.now()
        self.monto = monto
        self.tipo = tipo
        self.descripcion = descripcion
        self.cuenta_origen = cta_origen
        self.cuenta_destino = cta_destino

    def guardar(self):
        """Registra el movimiento en el historial."""
        conexion = conectar_bd()
        try:
            cursor = conexion.execute("""
                INSERT INTO movimientos (id_cuenta, fecha, monto, tipo, descripcion, nro_cuenta_origen, nro_cuenta_destino)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (self.id_cuenta_bd, self.fecha, self.monto, self.tipo, self.descripcion, self.cuenta_origen, self.cuenta_destino))
            conexion.commit()
            self.id_bd = cursor.lastrowid
        finally:
            conexion.close()

class CuentaBase(ABC):
    def __init__(self, numero, titular, categoria, saldo=0, id_bd=None):
        self.numero = numero
        self.titular = titular
        self.categoria = categoria 
        self._saldo = saldo
        self.id_bd = id_bd
    
    @property
    def saldo(self): return self._saldo
    
    @abstractmethod
    def puede_extraer(self, monto): pass

    def guardar(self):
        """Guarda la cuenta en la BD."""
        conexion = conectar_bd()
        tipo_str = "CA" if isinstance(self, CajaAhorro) else "CC"
        limite = getattr(self, 'limite_descubierto', None)
        costo = getattr(self, 'costo_mantenimiento', None)
        f_creacion = date.today()
        try:
            cursor = conexion.execute("""
                INSERT INTO cuentas (numero, saldo, tipo_cuenta, categoria, id_cliente, 
                                  limite_descubierto, costo_mantenimiento, fecha_creacion) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, (self.numero, self._saldo, tipo_str, self.categoria, self.titular.id_bd, 
                                      limite, costo, f_creacion))
            conexion.commit()
            self.id_bd = cursor.lastrowid
        finally: conexion.close()
        return self
    
    def _actualizar_saldo_bd(self):
        """Actualización rápida del saldo."""
        if self.id_bd:
            conexion = conectar_bd()
            try:
                conexion.execute("UPDATE cuentas SET saldo = ? WHERE id = ?", (self._saldo, self.id_bd))
                conexion.commit()
            finally: conexion.close()
    
    def depositar(self, monto):
        if monto <= 0: return None
        self._saldo += monto
        self._actualizar_saldo_bd()
        mov = Movimientos(monto, "Depósito", self.id_bd)
        mov.guardar()
        return mov
    
    def extraer(self, monto):
        if monto > 0 and self.puede_extraer(monto):
            self._saldo -= monto
            self._actualizar_saldo_bd()
            mov = Movimientos(monto, "Extracción", self.id_bd)
            mov.guardar()
            return mov
    
    def transferir(self, monto, destino, comision=0):
        if self.numero == destino.numero: return (None, None)
        monto_total = monto + comision
        if monto > 0 and self.puede_extraer(monto_total):
            self._saldo -= monto_total
            destino._saldo += monto
            self._actualizar_saldo_bd()
            destino._actualizar_saldo_bd()
            mov_origen = Movimientos(monto, "Transferencia Enviada", self.id_bd, cta_origen=self.numero, cta_destino=destino.numero)
            mov_origen.guardar()
            mov_destino = Movimientos(monto, "Transferencia Recibida", destino.id_bd, cta_origen=self.numero, cta_destino=destino.numero)
            mov_destino.guardar()
            return (mov_origen, mov_destino)
        return (None, None)

    # --- LÓGICA DE INVERSIONES (PLAZO FIJO) ---
    def constituir_plazo_fijo(self, monto, dias, tasa_anual):
        """Crea un PF descontando saldo real (no descubierto)."""
        if monto <= 0 or self._saldo < monto:
            return False
        
        interes = (monto * tasa_anual / 365) * dias
        monto_final = monto + interes
        f_creacion = date.today()
        f_vencimiento = f_creacion + timedelta(days=dias)
        
        conexion = conectar_bd()
        try:
            # Insertamos el PF
            conexion.execute("""
                INSERT INTO plazos_fijos (id_cuenta, monto_inicial, dias, tasa_interes, 
                                          monto_final, fecha_creacion, fecha_vencimiento, estado)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVO')
            """, (self.id_bd, monto, dias, tasa_anual, monto_final, f_creacion, f_vencimiento))
            
            # Descontamos saldo
            nuevo_saldo = self._saldo - monto
            conexion.execute("UPDATE cuentas SET saldo = ? WHERE id = ?", (nuevo_saldo, self.id_bd))
            
            # Guardamos movimiento
            desc = f"Constitución PF {dias} días"
            conexion.execute("""
                INSERT INTO movimientos (id_cuenta, fecha, monto, tipo, descripcion, nro_cuenta_origen, nro_cuenta_destino)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.id_bd, datetime.now(), monto, "Débito Plazo Fijo", desc, None, None))
            
            conexion.commit()
            self._saldo = nuevo_saldo
            return True
        except Exception as e:
            print(f"Error PF: {e}")
            return False
        finally: conexion.close()

    def cobrar_plazo_fijo(self, id_pf):
        """Cobra un PF si ya venció."""
        conexion = conectar_bd()
        pf = conexion.execute("SELECT * FROM plazos_fijos WHERE id = ?", (id_pf,)).fetchone()
        if not pf or pf['estado'] != 'ACTIVO':
            conexion.close()
            return "No válido"
        if date.today() < pf['fecha_vencimiento']:
            conexion.close()
            return "Aún no vence"
        
        monto_final = pf['monto_final']
        self._saldo += monto_final
        self._actualizar_saldo_bd()
        
        conexion.execute("UPDATE plazos_fijos SET estado = 'COBRADO' WHERE id = ?", (id_pf,))
        desc = f"Cobro PF N°{id_pf} (Interés: ${monto_final - pf['monto_inicial']:.2f})"
        
        mov = Movimientos(monto_final, "Acreditación Plazo Fijo", self.id_bd, desc)
        mov.guardar()
        conexion.commit()
        conexion.close()
        return "OK"

    def obtener_mis_plazos_fijos(self):
        """Lista todos los PFs asociados a esta cuenta."""
        conexion = conectar_bd()
        filas = conexion.execute("SELECT * FROM plazos_fijos WHERE id_cuenta = ? ORDER BY fecha_vencimiento DESC", (self.id_bd,)).fetchall()
        conexion.close()
        return filas

    # --- MÉTODOS DE RECUPERACIÓN (Active Record) ---
    @staticmethod
    def buscar_por_numero(numero):
        """Recupera una cuenta por su número único."""
        conexion = conectar_bd()
        fila = conexion.execute("""
            SELECT cuentas.*, clientes.nombre, clientes.apellido, clientes.dni, clientes.email, clientes.activo
            FROM cuentas JOIN clientes ON cuentas.id_cliente = clientes.id
            WHERE cuentas.numero = ?
            """, (numero,)).fetchone()
        conexion.close()
        if fila: return CuentaBase._reconstruir_desde_fila(fila)
        return None
    
    @staticmethod
    def recuperar_por_cliente(id_cliente):
        """Recupera todas las cuentas de un cliente."""
        conexion = conectar_bd()
        fila_cli = conexion.execute("SELECT * FROM clientes WHERE id = ?", (id_cliente,)).fetchone()
        if not fila_cli: 
            conexion.close()
            return []
        titular = Cliente(fila_cli['nombre'], fila_cli['apellido'], fila_cli['dni'], fila_cli['email'], fila_cli['activo'], fila_cli['id'])
        filas = conexion.execute("SELECT * FROM cuentas WHERE id_cliente = ?", (id_cliente,)).fetchall()
        conexion.close()
        cuentas = []
        for fila in filas:
            cuentas.append(CuentaBase._reconstruir_desde_fila(fila, titular_ya_cargado=titular))
        return cuentas
    
    @staticmethod
    def _reconstruir_desde_fila(fila, titular_ya_cargado=None):
        """Helper para convertir fila de BD a Objeto Python."""
        if titular_ya_cargado: titular = titular_ya_cargado
        else:
            titular = Cliente(fila['nombre'], fila['apellido'], fila['dni'], fila['email'], fila['activo'])
            titular.id_bd = fila['id_cliente']
        tipo = fila['tipo_cuenta']
        categoria = fila['categoria']
        if tipo == 'CA': c = CajaAhorro(fila['numero'], titular, categoria, fila['saldo'])
        elif tipo == 'CC': c = CuentaCorriente(fila['numero'], titular, categoria, fila['saldo'], fila['limite_descubierto'], fila['costo_mantenimiento'])
        else: return None
        c.id_bd = fila['id']
        return c

class CajaAhorro(CuentaBase):
    def puede_extraer(self, monto): return monto <= self._saldo
    def aplicar_mantenimiento(self): return 0

class CuentaCorriente(CuentaBase):
    def __init__(self, numero, titular, categoria, saldo=0, limite_descubierto=0, costo_mantenimiento=0):
        super().__init__(numero, titular, categoria, saldo)
        self.limite_descubierto = limite_descubierto
        self.costo_mantenimiento = costo_mantenimiento
    def puede_extraer(self, monto): return monto <= (self._saldo + self.limite_descubierto)
    def aplicar_mantenimiento(self):
        descuento = 0.10 if self.categoria == "Empresa" else 0.0
        costo_final = self.costo_mantenimiento * (1 - descuento)
        self._saldo -= costo_final
        self._actualizar_saldo_bd()
        return costo_final

# --- CLASE PRINCIPAL: BANCO ---

class Banco:
    def __init__(self, nombre):
        self.nombre = nombre
        self.cargar_configuracion_db()
    
    def cargar_configuracion_db(self):
        """Carga parámetros globales (tasas, contadores)."""
        conexion = conectar_bd()
        fila = conexion.execute("SELECT * FROM parametros WHERE id=1").fetchone()
        conexion.close()
        if fila:
            self.comision_transferencia = fila['comision_transferencia']
            self.default_tasa_anual_pf = fila['tasa_anual_pf']
            self.default_costo_mantenimiento_cc = fila['costo_mantenimiento_cc']
            self.default_limite_descubierto_cc = fila['limite_descubierto_cc']
            self.ultimo_nro_cuenta = fila['ultimo_nro_cuenta']
        else:
            self.comision_transferencia = 50.0
            self.default_tasa_anual_pf = 0.45
            self.default_costo_mantenimiento_cc = 100.0
            self.default_limite_descubierto_cc = 10000.0
            self.ultimo_nro_cuenta = 0
    
    def guardar_configuracion_db(self):
        conexion = conectar_bd()
        try:
            conexion.execute("""
                UPDATE parametros SET comision_transferencia=?, tasa_anual_pf=?, costo_mantenimiento_cc=?, limite_descubierto_cc=?, ultimo_nro_cuenta = ? 
                WHERE id = 1
            """, (self.comision_transferencia, self.default_tasa_anual_pf, self.default_costo_mantenimiento_cc, self.default_limite_descubierto_cc, self.ultimo_nro_cuenta))
            conexion.commit()
        finally: conexion.close()
    
    def generar_numero_cuenta(self):
        self.ultimo_nro_cuenta += 1 
        self.guardar_configuracion_db() 
        return self.ultimo_nro_cuenta
    
    def obtener_datos_reporte_global(self):
        """Datos crudos para exportar a CSV."""
        conexion = conectar_bd()
        sql = """
            SELECT cuentas.numero, cuentas.tipo_cuenta, cuentas.categoria, cuentas.saldo, 
                   clientes.nombre, clientes.apellido, clientes.dni, clientes.email, clientes.activo 
            FROM cuentas JOIN clientes ON cuentas.id_cliente = clientes.id
        """
        filas = conexion.execute(sql).fetchall()
        conexion.close()
        return filas

    def buscar_cuentas_filtro(self, termino):
        """Buscador en tiempo real por número, DNI o apellido."""
        conexion = conectar_bd()
        termino_like = f"%{termino}%"
        sql = """
            SELECT cuentas.*, clientes.nombre, clientes.apellido, clientes.dni, clientes.email, clientes.activo
            FROM cuentas JOIN clientes ON cuentas.id_cliente = clientes.id
            WHERE cuentas.numero LIKE ? OR clientes.dni LIKE ? OR clientes.apellido LIKE ?
        """
        filas = conexion.execute(sql, (termino_like, termino_like, termino_like)).fetchall()
        conexion.close()
        cuentas_encontradas = []
        for f in filas:
            obj = CuentaBase._reconstruir_desde_fila(f)
            if obj: cuentas_encontradas.append(obj)
        return cuentas_encontradas

    def buscar_clientes_filtro(self, termino):
        """Buscador de clientes en tiempo real."""
        conexion = conectar_bd()
        termino_like = f"%{termino}%"
        sql = """
            SELECT * FROM clientes
            WHERE dni LIKE ? OR nombre LIKE ? OR apellido LIKE ?
        """
        filas = conexion.execute(sql, (termino_like, termino_like, termino_like)).fetchall()
        conexion.close()
        clientes_encontrados = []
        for f in filas:
            c = Cliente(f['nombre'], f['apellido'], f['dni'], f['email'], f['activo'])
            c.id_bd = f['id']
            clientes_encontrados.append(c)
        return clientes_encontrados

    def obtener_movimientos_para_analisis(self, filtros):
        """
        Recupera TODOS los datos detallados para el Panel de Análisis (Gráficos).
        Realiza JOIN con Clientes y Cuentas para tener nombre, tipo, etc.
        """
        conexion = conectar_bd()
        sql = """
            SELECT 
                m.fecha, 
                m.tipo, 
                m.monto, 
                m.descripcion, 
                m.nro_cuenta_origen, 
                m.nro_cuenta_destino,
                c.numero as nro_cuenta,
                c.categoria,
                cl.nombre,     -- Datos del cliente para la tabla
                cl.apellido
            FROM movimientos m
            JOIN cuentas c ON m.id_cuenta = c.id
            JOIN clientes cl ON c.id_cliente = cl.id
            WHERE m.fecha BETWEEN ? AND ?
        """
        
        f_desde = datetime.combine(filtros['desde'], datetime.min.time())
        f_hasta = datetime.combine(filtros['hasta'], datetime.max.time())
        params = [f_desde, f_hasta]
        
        # Filtro Categoria Cliente
        if filtros['tipo_cliente'] != "Todos":
            sql += " AND c.categoria = ?"
            params.append(filtros['tipo_cliente'])
            
        # Filtro Tipo Movimiento
        if filtros['tipo_movimiento'] != "Todos":
            sql += " AND m.tipo LIKE ?"
            params.append(f"%{filtros['tipo_movimiento']}%")
            
        sql += " ORDER BY m.fecha DESC"
        
        filas = conexion.execute(sql, params).fetchall()
        conexion.close()
        return filas

# Inicializar BD al importar
inicializar_bd()