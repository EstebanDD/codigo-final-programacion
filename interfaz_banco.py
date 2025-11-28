# -*- coding: utf-8 -*-

import sys
import csv
import sqlite3
from datetime import datetime, date, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QFrame,
    QTextEdit, QDialog, QLineEdit, QComboBox, QDialogButtonBox, QFormLayout,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit, QFileDialog,
    QHBoxLayout, QGridLayout, QTabWidget, QAbstractItemView, QGroupBox
)
from PyQt6.QtCore import Qt, QDate, QRegularExpression
from PyQt6.QtGui import QDoubleValidator, QIntValidator, QRegularExpressionValidator
import codigo_banco as logica

# --- SECCIÓN: IMPORTS PARA GRÁFICOS ---
# Matplotlib tiene diferentes "backends" para conectarse con distintas interfaces.
# Aquí intentamos importar el backend moderno de Qt6, y si falla, usamos el de Qt5 (compatible).
import matplotlib.pyplot as plt
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.dates as mdates

# ==========================================
# VENTANA PRINCIPAL
# ==========================================
class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema Bancario - Banco POO")
        self.setGeometry(100,100,500,450)
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QHBoxLayout(widget_central)
        layout_botones = QVBoxLayout()
        titulo = QLabel("Banco POO\nMenú Principal")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = titulo.font()
        font.setPointSize(18)
        font.setBold(True)
        titulo.setFont(font)
        layout_botones.addWidget(titulo)
        estilo = "font-size: 14px; padding: 15px;"
        
        # Botones del menú
        self.btn_crear = QPushButton("1. Crear Cuenta")
        self.btn_crear.setStyleSheet(estilo)
        self.btn_ingresar = QPushButton("2. Ingresar a Cuenta")
        self.btn_ingresar.setStyleSheet(estilo)
        self.btn_gestion = QPushButton("3. Gestión (Admin)")
        self.btn_gestion.setStyleSheet(estilo)
        self.btn_salir = QPushButton("0. Salir")
        self.btn_salir.setStyleSheet("font-size: 12px; padding: 10px;")
        
        layout_botones.addSpacing(20)
        layout_botones.addWidget(self.btn_crear)
        layout_botones.addWidget(self.btn_ingresar)
        layout_botones.addWidget(self.btn_gestion)
        layout_botones.addStretch()
        layout_botones.addWidget(self.btn_salir)
        layout_principal.addStretch(1)
        layout_principal.addLayout(layout_botones, 2)
        layout_principal.addStretch(1)

# ==========================================
# DIÁLOGOS DE CREACIÓN Y LOGIN
# ==========================================
class DialogoCrearCuenta(QDialog):
    """Ventana para registrar un nuevo cliente y su primera cuenta."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crear Nueva Cuenta")
        self.resize(400, 300)
        layout = QFormLayout(self)
        
        self.campo_nombre = QLineEdit()
        self.campo_apellido = QLineEdit()
        self.campo_dni = QLineEdit()
        self.campo_dni.setValidator(QIntValidator()) # Solo números
        self.campo_email = QLineEdit()
        self.campo_email.setPlaceholderText("Opcional")
        
        self.combo_categoria = QComboBox() 
        self.combo_categoria.addItems(["Persona", "Empresa"])
        
        self.combo_tipo_cuenta = QComboBox()
        self.combo_tipo_cuenta.addItems(["Caja de Ahorro", "Cuenta Corriente"])
        
        layout.addRow("Nombre:", self.campo_nombre)
        layout.addRow("Apellido:", self.campo_apellido)
        layout.addRow("DNI:", self.campo_dni)
        layout.addRow("Email:", self.campo_email)
        layout.addRow("Categoría Cuenta:", self.combo_categoria)
        layout.addRow("Tipo Producto:", self.combo_tipo_cuenta)
        
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        
    def obtener_datos(self):
        return {
            "nombre": self.campo_nombre.text().strip().title(),
            "apellido": self.campo_apellido.text().strip().title(),
            "dni": self.campo_dni.text().strip(),
            "email": self.campo_email.text().strip(),
            "categoria": self.combo_categoria.currentText(),
            "tipo_cuenta": self.combo_tipo_cuenta.currentText()
        }

class DialogoLogin(QDialog):
    """Login simple usando solo el DNI."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ingresar a Cuenta")
        self.resize(300, 100)
        layout = QFormLayout(self)
        self.campo_dni = QLineEdit()
        self.campo_dni.setValidator(QIntValidator())
        layout.addRow("Ingrese su DNI:", self.campo_dni)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
    def obtener_dni(self): return self.campo_dni.text().strip()

# ==========================================
# SECCIÓN DE GESTIÓN (ADMINISTRADOR)
# ==========================================

class DialogoLoginAdmin(QDialog):
    """Acceso seguro con usuario y contraseña."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acceso Administrativo")
        self.resize(300, 150)
        layout = QFormLayout(self)
        self.user = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password) # Oculta caracteres
        layout.addRow("Usuario:", self.user)
        layout.addRow("Contraseña:", self.password)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        botones.accepted.connect(self.validar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
    def validar(self):
        if self.user.text() == "admin" and self.password.text() == "1234": self.accept()
        else: QMessageBox.warning(self, "Error", "Credenciales incorrectas")

class VentanaGestion(QDialog):
    """Panel principal del administrador."""
    def __init__(self, banco, controlador, parent=None):
        super().__init__(parent)
        self.banco = banco
        self.controlador = controlador
        self.setWindowTitle("Panel de Gestión")
        self.resize(400, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Opciones Administrativas</h2>"))
        
        btn_params = QPushButton("Ajustar Parámetros del Banco")
        btn_params.clicked.connect(self.ajustar_parametros)
        
        btn_informe = QPushButton("Generar Informe Global (CSV)")
        btn_informe.clicked.connect(self.generar_informe)
        
        btn_saldo = QPushButton("Ver Saldo Total Banco")
        btn_saldo.clicked.connect(self.ver_saldo_total)
        
        btn_clientes = QPushButton("Gestión de Clientes (Baja)")
        btn_clientes.clicked.connect(self.gestionar_clientes)
        
        btn_buscar = QPushButton("Buscar Cuentas (Consulta)")
        btn_buscar.clicked.connect(self.buscar_cuentas_admin)
        
        # Botón para abrir el Dashboard de Análisis
        btn_graficos = QPushButton("Ver Gráficas de la Empresa")
        btn_graficos.clicked.connect(self.ver_graficos)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.close)
        
        for btn in [btn_params, btn_informe, btn_saldo, btn_clientes, btn_buscar, btn_graficos]:
            btn.setStyleSheet("padding: 10px; font-size: 13px; text-align: left;")
            layout.addWidget(btn)
        layout.addStretch()
        layout.addWidget(btn_cerrar)

    def ajustar_parametros(self): self.controlador.ajustar_parametros(self)
    def generar_informe(self): self.controlador.generar_informe(self)
    def ver_saldo_total(self): self.controlador.ver_saldo_total(self)
    def gestionar_clientes(self):
        ventana = VentanaBajaCliente(self.banco, self)
        ventana.exec()
    def buscar_cuentas_admin(self):
        dialogo = DialogoBuscadorCuentas(self.banco, parent=self)
        dialogo.exec()
    def ver_graficos(self):
        # Llama a la ventana integrada de análisis
        ventana = VentanaAnalisis(self.banco, self)
        ventana.exec()

class VentanaBajaCliente(QDialog):
    """Buscador y gestión de estado de clientes (Baja lógica / Reactivación)."""
    def __init__(self, banco, parent=None):
        super().__init__(parent)
        self.banco = banco
        self.setWindowTitle("Gestión de Clientes - Estado")
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Escriba DNI o Nombre para filtrar...")
        self.txt_buscar.textChanged.connect(self.actualizar_lista)
        layout.addWidget(self.txt_buscar)
        
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["DNI", "Nombre", "Apellido", "Estado"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.clicked.connect(self.seleccionar_cliente)
        layout.addWidget(self.tabla)
        
        self.lbl_detalles = QLabel("Seleccione un cliente de la lista para ver detalles.")
        self.lbl_detalles.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.lbl_detalles.setWordWrap(True)
        self.lbl_detalles.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.lbl_detalles)
        
        h_botones = QHBoxLayout()
        self.btn_baja = QPushButton("Dar de Baja")
        self.btn_baja.setStyleSheet("background-color: #ffcccc; color: red; font-weight: bold;")
        self.btn_baja.setEnabled(False)
        self.btn_baja.clicked.connect(self.dar_de_baja)
        
        self.btn_reactivar = QPushButton("Reactivar")
        self.btn_reactivar.setStyleSheet("background-color: #ccffcc; color: green; font-weight: bold;")
        self.btn_reactivar.setEnabled(False)
        self.btn_reactivar.clicked.connect(self.reactivar_cliente)
        
        h_botones.addWidget(self.btn_baja)
        h_botones.addWidget(self.btn_reactivar)
        layout.addLayout(h_botones)
        self.cliente_seleccionado = None
        self.actualizar_lista()

    def actualizar_lista(self):
        termino = self.txt_buscar.text().strip()
        clientes = self.banco.buscar_clientes_filtro(termino)
        self.tabla.setRowCount(len(clientes))
        for i, c in enumerate(clientes):
            estado = "ACTIVO" if c.activo == 1 else "BAJA"
            self.tabla.setItem(i, 0, QTableWidgetItem(c.dni))
            self.tabla.setItem(i, 1, QTableWidgetItem(c.nombre))
            self.tabla.setItem(i, 2, QTableWidgetItem(c.apellido))
            self.tabla.setItem(i, 3, QTableWidgetItem(estado))
            self.tabla.item(i, 0).setData(Qt.ItemDataRole.UserRole, c)

    def seleccionar_cliente(self):
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.cliente_seleccionado = self.tabla.item(fila, 0).data(Qt.ItemDataRole.UserRole)
            self.mostrar_detalles()

    def mostrar_detalles(self):
        c = self.cliente_seleccionado
        if not c: return
        cuentas = logica.CuentaBase.recuperar_por_cliente(c.id_bd)
        estado_txt = "ACTIVO" if c.activo == 1 else "INACTIVO"
        color = "green" if c.activo == 1 else "red"
        info = f"<h2>{c.nombre} {c.apellido}</h2>" \
               f"<b>DNI:</b> {c.dni}<br>" \
               f"<b>Estado:</b> <span style='color:{color}; font-weight:bold'>{estado_txt}</span><br><br>" \
               f"<b>Cuentas:</b><br>"
        if cuentas:
            for cta in cuentas:
                tipo = "CA" if isinstance(cta, logica.CajaAhorro) else "CC"
                info += f"• {tipo} ({cta.categoria}) - ${cta.saldo:.2f}<br>"
        else: info += "<i>Sin cuentas.</i>"
        self.lbl_detalles.setText(info)
        self.btn_baja.setEnabled(c.activo == 1)
        self.btn_reactivar.setEnabled(c.activo == 0)

    def dar_de_baja(self):
        if not self.cliente_seleccionado: return
        res = QMessageBox.question(self, "Confirmar", f"¿Dar de baja a {self.cliente_seleccionado.nombre}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            self.cliente_seleccionado.dar_de_baja()
            self.actualizar_lista()
            self.lbl_detalles.setText("Cliente actualizado.")
            self.btn_baja.setEnabled(False)

    def reactivar_cliente(self):
        if not self.cliente_seleccionado: return
        res = QMessageBox.question(self, "Confirmar", f"¿Reactivar a {self.cliente_seleccionado.nombre}? (Saldos a 0)", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if res == QMessageBox.StandardButton.Yes:
            self.cliente_seleccionado.reactivar()
            self.actualizar_lista()
            self.lbl_detalles.setText("Cliente actualizado.")
            self.btn_reactivar.setEnabled(False)

class DialogoAjustarParametros(QDialog):
    def __init__(self, banco, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parámetros")
        layout = QFormLayout(self)
        self.pf = QLineEdit(str(banco.default_tasa_anual_pf))
        self.cc_costo = QLineEdit(str(banco.default_costo_mantenimiento_cc))
        self.cc_lim = QLineEdit(str(banco.default_limite_descubierto_cc))
        self.com = QLineEdit(str(banco.comision_transferencia))
        layout.addRow("Tasa PF:", self.pf)
        layout.addRow("Costo CC:", self.cc_costo)
        layout.addRow("Límite CC:", self.cc_lim)
        layout.addRow("Comisión:", self.com)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
    def obtener_parametros(self):
        return {"tasa_pf": self.pf.text(), "costo_cc": self.cc_costo.text(), "descubierto_cc": self.cc_lim.text(), "comision": self.com.text()}

# =========================================================
# 4. VENTANA DE ANÁLISIS FINANCIERO (DASHBOARD COMPLETO)
# =========================================================

class VentanaAnalisis(QDialog):
    """
    Ventana que integra:
    - Filtros superiores en vivo.
    - Tabla de movimientos a la izquierda (incluye nombre Cliente).
    - Resumen de totales y Gráfico de Torta a la derecha.
    """
    def __init__(self, banco, parent=None):
        super().__init__(parent)
        self.banco = banco  # Necesitamos el banco para pedir datos
        self.setWindowTitle("Panel de Análisis Financiero")
        self.resize(1100, 700)
        
        layout_main = QVBoxLayout(self)
        
        # --- A. FILTROS SUPERIORES ---
        group_filtros = QGroupBox("Filtros de Visualización")
        layout_filtros = QHBoxLayout(group_filtros)
        
        layout_filtros.addWidget(QLabel("Cliente:"))
        self.combo_cliente = QComboBox()
        self.combo_cliente.addItems(["Todos", "Persona", "Empresa"])
        layout_filtros.addWidget(self.combo_cliente)
        
        layout_filtros.addWidget(QLabel("Movimiento:"))
        self.combo_movimiento = QComboBox()
        self.combo_movimiento.addItems(["Todos", "Depósito", "Extracción", "Transferencia", "Plazo Fijo"])
        layout_filtros.addWidget(self.combo_movimiento)
        
        layout_filtros.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_desde.setCalendarPopup(True)
        layout_filtros.addWidget(self.date_desde)
        
        layout_filtros.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit(QDate.currentDate())
        self.date_hasta.setCalendarPopup(True)
        layout_filtros.addWidget(self.date_hasta)
        
        self.btn_actualizar = QPushButton("Aplicar Filtros")
        self.btn_actualizar.setStyleSheet("font-weight: bold; background-color: #0078d7; color: white; padding: 5px 15px;")
        self.btn_actualizar.clicked.connect(self.actualizar_datos)
        layout_filtros.addWidget(self.btn_actualizar)
        
        layout_main.addWidget(group_filtros)
        
        # --- B. ÁREA PRINCIPAL ---
        cuerpo_h = QHBoxLayout()
        
        # IZQUIERDA: Tabla
        frame_izq = QFrame()
        layout_izq = QVBoxLayout(frame_izq)
        layout_izq.addWidget(QLabel("<h3>Detalle de Movimientos</h3>"))
        
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["Cliente", "Fecha", "Cta", "Tipo", "Monto", "Desc"])
        self.tabla.setAlternatingRowColors(True)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout_izq.addWidget(self.tabla)
        
        cuerpo_h.addWidget(frame_izq, 1) # Factor 1 (50% ancho)

        # DERECHA: Resumen + Gráfico
        frame_der = QFrame()
        layout_der = QVBoxLayout(frame_der)
        
        # B1. Resumen Numérico
        group_resumen = QGroupBox("Resumen de Totales")
        layout_resumen = QGridLayout(group_resumen)
        self.lbl_dep = QLabel("$0.00")
        self.lbl_ext = QLabel("$0.00")
        self.lbl_trans = QLabel("$0.00")
        self.lbl_pf = QLabel("$0.00")
        
        layout_resumen.addWidget(QLabel("Depositado:"), 0, 0)
        layout_resumen.addWidget(self.lbl_dep, 0, 1)
        layout_resumen.addWidget(QLabel("Extraído:"), 1, 0)
        layout_resumen.addWidget(self.lbl_ext, 1, 1)
        layout_resumen.addWidget(QLabel("Transferido:"), 2, 0)
        layout_resumen.addWidget(self.lbl_trans, 2, 1)
        layout_resumen.addWidget(QLabel("Plazo Fijo:"), 3, 0)
        layout_resumen.addWidget(self.lbl_pf, 3, 1)
        
        layout_der.addWidget(group_resumen)
        
        # B2. Gráfico (Matplotlib)
        layout_der.addWidget(QLabel("<h3>Distribución de Volumen</h3>"))
        # Creamos la figura y el canvas
        self.figura, self.ax = plt.subplots(figsize=(4, 3))
        self.canvas = FigureCanvas(self.figura)
        layout_der.addWidget(self.canvas)
        
        cuerpo_h.addWidget(frame_der, 1) # Factor 1 (50% ancho)
        
        layout_main.addLayout(cuerpo_h)
        
        btn_cerrar = QPushButton("Cerrar Panel")
        btn_cerrar.clicked.connect(self.accept)
        layout_main.addWidget(btn_cerrar)

        self.actualizar_datos() # Carga inicial

    def actualizar_datos(self):
        # 1. Leer filtros
        filtros = {
            "tipo_cliente": self.combo_cliente.currentText(),
            "tipo_movimiento": self.combo_movimiento.currentText(),
            "desde": self.date_desde.date().toPyDate(),
            "hasta": self.date_hasta.date().toPyDate()
        }
        
        # 2. Consultar BD
        filas = self.banco.obtener_movimientos_para_analisis(filtros)
        
        # 3. Resetear acumuladores
        self.total_deposito = 0.0
        self.total_extraccion = 0.0
        self.total_transferencia = 0.0
        self.total_plazo_fijo = 0.0
        
        # 4. Llenar Tabla
        self.tabla.setRowCount(len(filas))
        for i, f in enumerate(filas):
            nombre = f"{f['nombre']} {f['apellido']}"
            fecha_str = f['fecha'].strftime('%d/%m/%Y')
            monto = f['monto']
            tipo = f['tipo']
            
            self.tabla.setItem(i, 0, QTableWidgetItem(nombre))
            self.tabla.setItem(i, 1, QTableWidgetItem(fecha_str))
            self.tabla.setItem(i, 2, QTableWidgetItem(f['nro_cuenta']))
            self.tabla.setItem(i, 3, QTableWidgetItem(tipo))
            self.tabla.setItem(i, 4, QTableWidgetItem(f"${monto:,.2f}"))
            self.tabla.setItem(i, 5, QTableWidgetItem(f['descripcion'] or ""))
            
            # Clasificar para totales
            if "Depósito" in tipo or "Acreditación" in tipo: self.total_deposito += monto
            elif "Extracción" in tipo: self.total_extraccion += monto
            elif "Transferencia" in tipo: self.total_transferencia += monto
            elif "Plazo Fijo" in tipo: self.total_plazo_fijo += monto
            
        # 5. Actualizar Resumen Visual
        estilo = "font-size: 14px; font-weight: bold;"
        self.lbl_dep.setText(f"${self.total_deposito:,.2f}")
        self.lbl_dep.setStyleSheet(f"color: green; {estilo}")
        self.lbl_ext.setText(f"${self.total_extraccion:,.2f}")
        self.lbl_ext.setStyleSheet(f"color: red; {estilo}")
        self.lbl_trans.setText(f"${self.total_transferencia:,.2f}")
        self.lbl_trans.setStyleSheet(f"color: blue; {estilo}")
        self.lbl_pf.setText(f"${self.total_plazo_fijo:,.2f}")
        self.lbl_pf.setStyleSheet(f"color: orange; {estilo}")
        
        # 6. Dibujar Gráfico
        self.generar_pie_chart()

    def generar_pie_chart(self):
        self.ax.clear()
        etiquetas = []
        valores = []
        colores = []
        
        if self.total_deposito > 0:
            etiquetas.append("Depósitos")
            valores.append(self.total_deposito)
            colores.append("#66bb6a")
        if self.total_extraccion > 0:
            etiquetas.append("Extracciones")
            valores.append(self.total_extraccion)
            colores.append("#ef5350")
        if self.total_transferencia > 0:
            etiquetas.append("Transferencias")
            valores.append(self.total_transferencia)
            colores.append("#42a5f5")
        if self.total_plazo_fijo > 0:
            etiquetas.append("Plazo Fijo")
            valores.append(self.total_plazo_fijo)
            colores.append("#ffca28")

        if not valores:
            self.ax.text(0.5, 0.5, "Sin datos para graficar", ha='center')
        else:
            self.ax.pie(valores, labels=etiquetas, colors=colores, autopct='%1.1f%%', startangle=90)
            self.ax.axis('equal')
        
        self.canvas.draw()

# ==========================================
# 5. UTILIDADES DE BÚSQUEDA Y TRANSACCIÓN
# ==========================================

class DialogoBuscadorCuentas(QDialog):
    def __init__(self, banco, parent=None):
        super().__init__(parent)
        self.banco = banco
        self.setWindowTitle("Buscador de Cuentas")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Escriba Número, DNI o Apellido...")
        self.txt_buscar.textChanged.connect(self.buscar)
        layout.addWidget(self.txt_buscar)
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["Nro Cuenta", "Titular", "Tipo", "DNI"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.doubleClicked.connect(self.seleccionar)
        layout.addWidget(self.tabla)
        h = QHBoxLayout()
        btn_seleccionar = QPushButton("Seleccionar")
        btn_seleccionar.clicked.connect(self.seleccionar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        h.addWidget(btn_seleccionar)
        h.addWidget(btn_cancelar)
        layout.addLayout(h)
        self.cuenta_seleccionada = None
        self.buscar()
    def buscar(self):
        termino = self.txt_buscar.text().strip()
        cuentas = self.banco.buscar_cuentas_filtro(termino)
        self.tabla.setRowCount(len(cuentas))
        for i, c in enumerate(cuentas):
            tipo = "CA" if isinstance(c, logica.CajaAhorro) else "CC"
            self.tabla.setItem(i, 0, QTableWidgetItem(c.numero))
            self.tabla.setItem(i, 1, QTableWidgetItem(f"{c.titular.nombre} {c.titular.apellido}"))
            self.tabla.setItem(i, 2, QTableWidgetItem(f"{tipo} ({c.categoria})"))
            self.tabla.setItem(i, 3, QTableWidgetItem(c.titular.dni))
            self.tabla.item(i, 0).setData(Qt.ItemDataRole.UserRole, c)
    def seleccionar(self):
        fila = self.tabla.currentRow()
        if fila >= 0:
            self.cuenta_seleccionada = self.tabla.item(fila, 0).data(Qt.ItemDataRole.UserRole)
            self.accept()

class DialogoPlazosFijos(QDialog):
    def __init__(self, cuenta, banco, parent=None):
        super().__init__(parent)
        self.cuenta = cuenta
        self.banco = banco
        self.setWindowTitle(f"Inversiones - Cuenta N°{cuenta.numero}")
        self.resize(500, 400)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tab_nuevo = QWidget()
        layout_nuevo = QFormLayout(tab_nuevo)
        self.lbl_saldo = QLabel(f"Saldo Disponible: ${cuenta.saldo:.2f}")
        self.lbl_saldo.setStyleSheet("font-weight: bold; color: green;")
        self.combo_dias = QComboBox()
        self.combo_dias.addItem("30 días", 30)
        self.combo_dias.addItem("60 días", 60)
        self.combo_dias.addItem("90 días", 90)
        self.campo_monto = QLineEdit()
        regex = QRegularExpression("^[0-9]+([.,][0-9]{1,2})?$")
        self.campo_monto.setValidator(QRegularExpressionValidator(regex))
        self.btn_constituir = QPushButton("Constituir Plazo Fijo")
        self.btn_constituir.clicked.connect(self.constituir)
        layout_nuevo.addRow(self.lbl_saldo)
        layout_nuevo.addRow("Plazo:", self.combo_dias)
        layout_nuevo.addRow("Monto:", self.campo_monto)
        layout_nuevo.addWidget(self.btn_constituir)
        tab_lista = QWidget()
        layout_lista = QVBoxLayout(tab_lista)
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(5)
        self.tabla.setHorizontalHeaderLabels(["ID", "Monto Final", "Vencimiento", "Estado", "Acción"])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout_lista.addWidget(self.tabla)
        tabs.addTab(tab_nuevo, "Nueva Inversión")
        tabs.addTab(tab_lista, "Mis Inversiones")
        layout.addWidget(tabs)
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)
        self.cargar_tabla()
    def constituir(self):
        try: monto = float(self.campo_monto.text().replace(',', '.'))
        except: 
            QMessageBox.warning(self, "Error", "Monto inválido")
            return
        dias = self.combo_dias.currentData()
        if self.cuenta.constituir_plazo_fijo(monto, dias, self.banco.default_tasa_anual_pf):
            QMessageBox.information(self, "Éxito", "Plazo Fijo constituido.")
            self.lbl_saldo.setText(f"Saldo Disponible: ${self.cuenta.saldo:.2f}")
            self.campo_monto.clear()
            self.cargar_tabla()
        else: QMessageBox.warning(self, "Error", "Saldo insuficiente o inválido.")
    def cargar_tabla(self):
        self.tabla.setRowCount(0)
        pfs = self.cuenta.obtener_mis_plazos_fijos()
        self.tabla.setRowCount(len(pfs))
        for i, pf in enumerate(pfs):
            self.tabla.setItem(i, 0, QTableWidgetItem(str(pf['id'])))
            self.tabla.setItem(i, 1, QTableWidgetItem(f"${pf['monto_final']:.2f}"))
            venc = pf['fecha_vencimiento']
            self.tabla.setItem(i, 2, QTableWidgetItem(venc.strftime('%d-%m-%Y')))
            self.tabla.setItem(i, 3, QTableWidgetItem(pf['estado']))
            if pf['estado'] == 'ACTIVO':
                btn = QPushButton("Cobrar")
                if date.today() >= venc:
                    btn.setEnabled(True)
                    btn.setStyleSheet("background-color: #ccffcc;")
                    btn.clicked.connect(lambda checked, pid=pf['id']: self.cobrar(pid))
                else:
                    btn.setEnabled(False)
                    btn.setText("En curso")
                self.tabla.setCellWidget(i, 4, btn)
            else: self.tabla.setItem(i, 4, QTableWidgetItem("-"))
    def cobrar(self, id_pf):
        res = self.cuenta.cobrar_plazo_fijo(id_pf)
        if res == "OK":
            QMessageBox.information(self, "Éxito", "Plazo Fijo acreditado.")
            self.lbl_saldo.setText(f"Saldo Disponible: ${self.cuenta.saldo:.2f}")
            self.cargar_tabla()
        else: QMessageBox.warning(self, "Error", f"{res}")

class DialogoMenuCliente(QDialog):
    def __init__(self, cliente, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Operaciones - {cliente.nombre}")
        self.setGeometry(150, 150, 600, 550)
        layout = QVBoxLayout(self)
        titulo = QLabel(f"Bienvenido, {cliente.nombre} {cliente.apellido}")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(titulo)
        layout.addWidget(QLabel("------------------------------------------------"))
        layout.addWidget(QLabel("Tus Cuentas:"))
        self.resumen_cuentas_texto = QTextEdit()
        self.resumen_cuentas_texto.setReadOnly(True)
        layout.addWidget(self.resumen_cuentas_texto)
        self.btn_consultar_saldo = QPushButton("Consultar Saldo")
        self.btn_depositar = QPushButton("Depositar")
        self.btn_extraer = QPushButton("Extraer")
        self.btn_transferir = QPushButton("Realizar Transferencia")
        self.btn_pf = QPushButton("Inversiones (Plazo Fijo)")
        self.btn_ver_movimientos = QPushButton("Ver Movimientos")
        self.btn_cerrar = QPushButton("Cerrar Sesión")
        layout.addWidget(self.btn_consultar_saldo)
        layout.addWidget(self.btn_depositar)
        layout.addWidget(self.btn_extraer)
        layout.addWidget(self.btn_transferir)
        layout.addWidget(self.btn_pf)
        layout.addWidget(self.btn_ver_movimientos)
        layout.addWidget(self.btn_cerrar)
        self.btn_cerrar.clicked.connect(self.accept)

class DialogoSeleccionarCuenta(QDialog):
    def __init__(self, cuentas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Cuenta")
        self.resize(500, 150)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Seleccione una cuenta:"))
        self.combo_cuentas = QComboBox()
        for cuenta in cuentas:
            tipo = "Caja Ahorro" if isinstance(cuenta, logica.CajaAhorro) else "Cta Corriente"
            texto = f"N°: {cuenta.numero} | {tipo} ({cuenta.categoria}) | ${cuenta.saldo:.2f}"
            self.combo_cuentas.addItem(texto, userData=cuenta)
        layout.addWidget(self.combo_cuentas)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
    def obtener_cuenta_seleccionada(self): return self.combo_cuentas.currentData()

class DialogoInputMonto(QDialog):
    def __init__(self, titulo, mensaje, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        layout = QFormLayout(self)
        self.campo_monto = QLineEdit()
        regex = QRegularExpression("^[0-9]+([.,][0-9]{1,2})?$")
        self.campo_monto.setValidator(QRegularExpressionValidator(regex))
        layout.addRow(mensaje, self.campo_monto)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
    def obtener_monto(self):
        try: return float(self.campo_monto.text().replace(',', '.'))
        except: return 0.0

class DialogoTransferencia(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transferencia")
        layout = QFormLayout(self)
        h = QHBoxLayout()
        self.txt_destino = QLineEdit()
        self.txt_destino.setReadOnly(True) 
        self.txt_destino.setPlaceholderText("Seleccione cuenta...")
        self.btn_buscar = QPushButton("Buscar Cuenta")
        h.addWidget(self.txt_destino)
        h.addWidget(self.btn_buscar)
        layout.addRow("Cuenta Destino:", h)
        self.campo_monto = QLineEdit()
        regex = QRegularExpression("^[0-9]+([.,][0-9]{1,2})?$")
        self.campo_monto.setValidator(QRegularExpressionValidator(regex))
        layout.addRow("Monto:", self.campo_monto)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
        self.nro_destino_seleccionado = None
    def conectar_buscador(self, funcion_buscador):
        self.btn_buscar.clicked.connect(funcion_buscador)
    def set_cuenta_destino(self, cuenta):
        self.nro_destino_seleccionado = int(cuenta.numero)
        self.txt_destino.setText(f"N° {cuenta.numero} - {cuenta.titular.nombre}")
    def obtener_datos_transferencia(self):
        try:
            monto = float(self.campo_monto.text().replace(',', '.'))
            if not self.nro_destino_seleccionado: return None, 0.0
            return self.nro_destino_seleccionado, monto
        except: return None, 0.0

class DialogoFiltrarMovimientos(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filtros")
        layout = QFormLayout(self)
        self.combo = QComboBox()
        self.combo.addItems(["Todos", "Depósito", "Extracción", "Transferencia", "Plazo Fijo"])
        self.desde = QDateEdit(QDate.currentDate().addMonths(-1))
        self.desde.setCalendarPopup(True)
        self.hasta = QDateEdit(QDate.currentDate())
        self.hasta.setCalendarPopup(True)
        layout.addRow("Tipo:", self.combo)
        layout.addRow("Desde:", self.desde)
        layout.addRow("Hasta:", self.hasta)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
    def obtener_filtros(self):
        return {"tipo": self.combo.currentText(), "desde": self.desde.date().toPyDate(), "hasta": self.hasta.date().toPyDate()}

class DialogoMostrarMovimientosEnTabla(QDialog):
    def __init__(self, titulo, filas, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.resize(600, 400)
        self.filas = filas
        layout = QVBoxLayout(self)
        self.tabla = QTableWidget()
        self.poblar_tabla()
        layout.addWidget(self.tabla)
        layout_botones = QHBoxLayout()
        self.btn_exportar = QPushButton("Exportar CSV")
        self.btn_cerrar = QPushButton("Cerrar")
        layout_botones.addWidget(self.btn_exportar)
        layout_botones.addWidget(self.btn_cerrar)
        layout.addLayout(layout_botones)
        self.btn_cerrar.clicked.connect(self.accept)
    def poblar_tabla(self):
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Tipo", "Monto", "Descripción", "Origen", "Destino"])
        self.tabla.setRowCount(len(self.filas))
        if not self.filas: return
        for i, fila in enumerate(self.filas):
            fecha_str = fila['fecha'].strftime('%d-%m-%Y %H:%M')
            monto_str = f"${fila['monto']:.2f}"
            self.tabla.setItem(i, 0, QTableWidgetItem(fecha_str))
            self.tabla.setItem(i, 1, QTableWidgetItem(fila['tipo']))
            self.tabla.setItem(i, 2, QTableWidgetItem(monto_str))
            self.tabla.setItem(i, 3, QTableWidgetItem(fila['descripcion'] or ""))
            self.tabla.setItem(i, 4, QTableWidgetItem(fila['nro_cuenta_origen'] or ""))
            self.tabla.setItem(i, 5, QTableWidgetItem(fila['nro_cuenta_destino'] or ""))
        self.tabla.resizeColumnsToContents()
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

# ==========================================
# 6. CONTROLADOR PRINCIPAL
# ==========================================

class ControladorApp:
    def __init__(self):
        logica.inicializar_bd()
        self.banco = logica.Banco(nombre="Banco POO")
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        self.ventana = VentanaPrincipal()
        self.conectar_botones()

    def conectar_botones(self):
        self.ventana.btn_crear.clicked.connect(self.crear_cuenta)
        self.ventana.btn_ingresar.clicked.connect(self.ingresar_a_cuenta)
        self.ventana.btn_gestion.clicked.connect(self.abrir_gestion)
        self.ventana.btn_salir.clicked.connect(self.salir)

    def iniciar(self):
        self.ventana.show()
        sys.exit(self.app.exec())

    def crear_cuenta(self):
        while True:
            dialogo = DialogoCrearCuenta(self.ventana)
            if not dialogo.exec(): return

            d = dialogo.obtener_datos()
            if not d["nombre"] or not d["apellido"] or not d["dni"]:
                QMessageBox.warning(self.ventana, "Error", "Faltan datos obligatorios.")
                continue
            
            cliente = logica.Cliente.buscar_por_dni(d["dni"])
            
            if cliente:
                if cliente.activo == 0:
                    QMessageBox.warning(self.ventana, "Aviso", "Cliente dado de baja.")
                    continue
            else:
                cliente = logica.Cliente(d["nombre"], d["apellido"], d["dni"], d["email"])
                if not cliente.guardar():
                    cliente = logica.Cliente.buscar_por_dni(d["dni"])
                    if not cliente:
                        QMessageBox.critical(self.ventana, "Error", "Error crítico BD.")
                        continue

            cuentas_existentes = logica.CuentaBase.recuperar_por_cliente(cliente.id_bd)
            categoria_solicitada = d["categoria"]
            tipo_solicitado = d["tipo_cuenta"]
            
            mapa_clases = {
                "Caja de Ahorro": logica.CajaAhorro,
                "Cuenta Corriente": logica.CuentaCorriente
            }
            clase_buscada = mapa_clases[tipo_solicitado]
            
            duplicada = False
            for c in cuentas_existentes:
                if isinstance(c, clase_buscada) and c.categoria == categoria_solicitada:
                    duplicada = True
                    break
            
            if duplicada:
                QMessageBox.warning(self.ventana, "Aviso", f"Ya posee una {tipo_solicitado} ({categoria_solicitada}).")
                continue

            nro = str(self.banco.generar_numero_cuenta())
            
            if tipo_solicitado == "Caja de Ahorro":
                cuenta = logica.CajaAhorro(nro, cliente, categoria_solicitada)
            else:
                cuenta = logica.CuentaCorriente(nro, cliente, categoria_solicitada, 0, self.banco.default_limite_descubierto_cc, self.banco.default_costo_mantenimiento_cc)
            
            cuenta.guardar()
            QMessageBox.information(self.ventana, "Éxito", f"Cuenta N°{nro} creada.")
            break

    def ingresar_a_cuenta(self):
        d = DialogoLogin(self.ventana)
        if not d.exec(): return
        dni = d.obtener_dni()

        cliente = logica.Cliente.buscar_por_dni(dni)
        if not cliente:
            QMessageBox.critical(self.ventana, "Error", "Cliente no encontrado.")
            return
        if cliente.activo == 0:
            QMessageBox.warning(self.ventana, "Acceso", "Cliente dado de baja.")
            return

        cuentas = logica.CuentaBase.recuperar_por_cliente(cliente.id_bd)
        if not cuentas:
            QMessageBox.warning(self.ventana, "Aviso", "Sin cuentas activas.")
            return

        self.abrir_menu_operaciones(cliente, cuentas)

    def abrir_menu_operaciones(self, cliente, cuentas):
        dialogo = DialogoMenuCliente(cliente, self.ventana)
        dialogo.btn_consultar_saldo.clicked.connect(lambda: self.cons_saldo(cuentas))
        dialogo.btn_depositar.clicked.connect(lambda: self.operar(cuentas, "deposito", dialogo))
        dialogo.btn_extraer.clicked.connect(lambda: self.operar(cuentas, "extraccion", dialogo))
        dialogo.btn_transferir.clicked.connect(lambda: self.transferir(cuentas, dialogo))
        dialogo.btn_pf.clicked.connect(lambda: self.abrir_plazos_fijos(cuentas, dialogo))
        dialogo.btn_ver_movimientos.clicked.connect(lambda: self.ver_movs(cuentas))
        self.actualizar_resumen(dialogo, cuentas)
        dialogo.exec()

    def actualizar_resumen(self, diag, cuentas):
        refresco = logica.CuentaBase.recuperar_por_cliente(cuentas[0].titular.id_bd)
        cuentas[:] = refresco
        txt = ""
        for c in cuentas:
            tipo_c = "CA" if isinstance(c, logica.CajaAhorro) else "CC"
            txt += f"{tipo_c} ({c.categoria}) N°{c.numero} | ${c.saldo:.2f}\n"
        diag.resumen_cuentas_texto.setText(txt)

    def abrir_plazos_fijos(self, cuentas, diag_padre):
        c = self.sel_cuenta(cuentas)
        if not c: return
        d = DialogoPlazosFijos(c, self.banco, diag_padre)
        d.exec()
        self.actualizar_resumen(diag_padre, cuentas)

    def cons_saldo(self, cuentas):
        c = self.sel_cuenta(cuentas)
        if c: QMessageBox.information(self.ventana, "Saldo", f"${c.saldo:.2f}")

    def sel_cuenta(self, cuentas):
        if not cuentas: return None
        if len(cuentas) == 1: return cuentas[0]
        d = DialogoSeleccionarCuenta(cuentas, self.ventana)
        if d.exec(): return d.obtener_cuenta_seleccionada()
        return None

    def operar(self, cuentas, tipo, diag_padre):
        c = self.sel_cuenta(cuentas)
        if not c: return
        d = DialogoInputMonto("Monto", "Ingrese monto:", self.ventana)
        if d.exec():
            monto = d.obtener_monto()
            res = c.depositar(monto) if tipo == "deposito" else c.extraer(monto)
            if res:
                QMessageBox.information(self.ventana, "Éxito", "Operación exitosa.")
                self.actualizar_resumen(diag_padre, cuentas)
            else:
                QMessageBox.warning(self.ventana, "Error", "Operación rechazada (Monto inválido o saldo insuf.)")

    def transferir(self, cuentas, diag_padre):
        c_orig = self.sel_cuenta(cuentas)
        if not c_orig: return
        d = DialogoTransferencia(self.ventana)
        d.conectar_buscador(lambda: self.abrir_buscador_transferencia(d))
        if not d.exec(): return
        nro_dest, monto = d.obtener_datos_transferencia()
        if str(nro_dest) == c_orig.numero:
            QMessageBox.warning(self.ventana, "Error", "Misma cuenta.")
            return
        c_dest = logica.CuentaBase.buscar_por_numero(str(nro_dest))
        if not c_dest:
            QMessageBox.critical(self.ventana, "Error", "Destino no existe.")
            return
        comision = self.banco.comision_transferencia if c_orig.titular.dni != c_dest.titular.dni else 0
        mov_orig, _ = c_orig.transferir(monto, c_dest, comision)
        if mov_orig:
            QMessageBox.information(self.ventana, "Éxito", "Transferencia OK.")
            self.actualizar_resumen(diag_padre, cuentas)
        else: QMessageBox.critical(self.ventana, "Error", "Fondos insuficientes.")

    def abrir_buscador_transferencia(self, dialogo_trans):
        d_bus = DialogoBuscadorCuentas(self.banco, parent=dialogo_trans)
        if d_bus.exec() and d_bus.cuenta_seleccionada:
            dialogo_trans.set_cuenta_destino(d_bus.cuenta_seleccionada)

    def ver_movs(self, cuentas):
        ids = [str(c.id_bd) for c in cuentas]
        while True:
            df = DialogoFiltrarMovimientos(self.ventana)
            if not df.exec(): break
            filtros = df.obtener_filtros()
            conn = logica.conectar_bd()
            q = f"SELECT * FROM movimientos WHERE id_cuenta IN ({','.join(['?']*len(ids))})"
            p = list(ids)
            f_desde = datetime.combine(filtros['desde'], datetime.min.time())
            f_hasta = datetime.combine(filtros['hasta'], datetime.max.time())
            q += " AND fecha BETWEEN ? AND ?"
            p.extend([f_desde, f_hasta])
            if filtros['tipo'] != "Todos":
                q += " AND tipo LIKE ?"
                p.append(f"{filtros['tipo']}%")
            q += " ORDER BY fecha DESC"
            rows = conn.execute(q, p).fetchall()
            conn.close()
            d = DialogoMostrarMovimientosEnTabla(f"Movimientos ({filtros['tipo']})", rows, self.ventana)
            d.btn_exportar.clicked.connect(lambda: self.exportar_movimientos_csv(rows))
            d.exec()

    def exportar_movimientos_csv(self, filas):
        nombre, _ = QFileDialog.getSaveFileName(self.ventana, "Guardar", "movs.csv", "CSV (*.csv)")
        if nombre:
            try:
                with open(nombre, 'w', newline='', encoding='utf-8') as f:
                    w = csv.writer(f, delimiter=';')
                    w.writerow(["Fecha", "Tipo", "Monto", "Desc", "Orig", "Dest"])
                    for r in filas:
                        fecha = r['fecha'].strftime('%Y-%m-%d %H:%M')
                        w.writerow([fecha, r['tipo'], str(r['monto']).replace('.',','), r['descripcion'], r['nro_cuenta_origen'], r['nro_cuenta_destino']])
                QMessageBox.information(self.ventana, "Éxito", "Guardado.")
            except Exception as e: QMessageBox.critical(self.ventana, "Error", str(e))

    def abrir_gestion(self):
        login = DialogoLoginAdmin(self.ventana)
        if login.exec():
            panel = VentanaGestion(self.banco, self, self.ventana)
            panel.exec()

    def ajustar_parametros(self, ventana_padre=None):
        parent = ventana_padre if ventana_padre else self.ventana
        d = DialogoAjustarParametros(self.banco, parent)
        if d.exec():
            p = d.obtener_parametros()
            try:
                self.banco.default_tasa_anual_pf = float(p["tasa_pf"])
                self.banco.default_costo_mantenimiento_cc = float(p["costo_cc"])
                self.banco.default_limite_descubierto_cc = float(p["descubierto_cc"])
                self.banco.comision_transferencia = float(p["comision"])
                self.banco.guardar_configuracion_db()
                QMessageBox.information(parent, "Éxito", "Parámetros actualizados.")
            except: QMessageBox.warning(parent, "Error", "Valores numéricos inválidos.")

    def generar_informe(self, ventana_padre=None):
        parent = ventana_padre if ventana_padre else self.ventana
        filas = self.banco.obtener_datos_reporte_global()
        if not filas:
            QMessageBox.warning(parent, "Aviso", "Sin datos.")
            return
        nombre, _ = QFileDialog.getSaveFileName(parent, "Reporte", f"reporte_{date.today()}.csv", "CSV (*.csv)")
        if nombre:
            try:
                with open(nombre, 'w', newline='', encoding='utf-8') as f:
                    w = csv.writer(f, delimiter=';')
                    w.writerow(["Nro", "Tipo", "Categoria", "Saldo", "Nombre", "Apellido", "DNI", "Email", "Activo"])
                    for fila in filas:
                        w.writerow([fila['numero'], fila['tipo_cuenta'], fila['categoria'], 
                                    str(fila['saldo']).replace('.',','), fila['nombre'], fila['apellido'], 
                                    fila['dni'], fila['email'], fila['activo']])
                QMessageBox.information(parent, "Éxito", "Reporte generado.")
            except Exception as e: QMessageBox.critical(parent, "Error", str(e))

    def ver_saldo_total(self, ventana_padre=None):
        padre = ventana_padre if ventana_padre else self.ventana
        conexion = logica.conectar_bd()
        total = conexion.execute("SELECT SUM(saldo) as total FROM cuentas").fetchone()['total'] or 0.0
        conexion.close()
        QMessageBox.information(padre, "Total", f"Total Activos: ${total:.2f}")

    def salir(self):
        self.app.quit()

if __name__ == "__main__":
    controlador = ControladorApp()
    controlador.iniciar()