import tkinter as tk
from tkinter import ttk
import serial
import time
import pymysql
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import ctypes
import winsound

# Obtener las dimensiones de la pantalla
user32 = ctypes.windll.user32
screen_width = user32.GetSystemMetrics(0)
screen_height = user32.GetSystemMetrics(1)

# Establecer la configuración de comunicación serial
arduino = serial.Serial('COM3', 9600)  # Cambia 'COM3' según el puerto en el que esté conectado tu Arduino
time.sleep(2)  # Esperar a que Arduino se reinicie

# Crear una conexión a la base de datos
connection = pymysql.connect(host='localhost', user='root', password='Cara.25818', database='signos_vitales')
cursor = connection.cursor()

# Verificar si la columna 'arritmia' no existe antes de agregarla
cursor.execute("SELECT * FROM information_schema.columns WHERE table_name = 'signos_vitales' AND column_name = 'arritmia'")
if cursor.fetchone() is None:
    # La columna 'arritmia' no existe, se agrega a la tabla
    cursor.execute("ALTER TABLE signos_vitales ADD COLUMN arritmia VARCHAR(20)")
    connection.commit()

# Etiqueta de frecuencia cardíaca
label_heart_rate = None

# Etiqueta de temperatura
label_temperature = None

# Etiqueta de arritmia
label_arrhythmia = None

# Figura y eje para el electrocardiograma
fig, ax = plt.subplots(figsize=(8, 4))

# Listas para almacenar los datos
fechas = []
frecuencias_cardiacas = []
temperaturas = []

def save_data(heart_rate, temperature):
    # Obtener la fecha y hora actual
    current_datetime = time.strftime('%Y-%m-%d %H:%M:%S')

    # Verificar si hay arritmia
    if int(heart_rate) > 100:
        arrhythmia = "Posible Arritmia"
        # Reproducir el sonido de alerta
        winsound.PlaySound("alert.wav", winsound.SND_ASYNC)
    else:
        arrhythmia = "Ritmo Cardíaco Regular"

    # Insertar los datos en la base de datos
    query = "INSERT INTO signos_vitales (fecha_hora, frecuencia_cardiaca, temperatura, arritmia) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (current_datetime, heart_rate, temperature, arrhythmia))
    connection.commit()

def read_sensors():
    global ax

    # Enviar comandos a Arduino para leer los datos de los sensores AD8232 y DS18B20
    arduino.write(b'H')  # Envía la letra 'H' a Arduino para leer la frecuencia cardíaca

    # Verificar si hay datos disponibles para leer
    if arduino.in_waiting > 0:
        heart_rate = arduino.readline().decode().strip()  # Leer la respuesta de Arduino y decodificarla

        arduino.write(b'T')  # Envía la letra 'T' a Arduino para leer la temperatura

        # Verificar si hay datos disponibles para leer
        if arduino.in_waiting > 0:
            temperature = arduino.readline().decode().strip()  # Leer la respuesta de Arduino y decodificarla

            # Guardar los datos en la base de datos
            save_data(heart_rate, temperature)

            # Actualizar las etiquetas de frecuencia cardíaca y temperatura
            label_heart_rate.config(text="Frecuencia Cardíaca: {} BPM".format(heart_rate))
            label_temperature.config(text="Temperatura: {} °C".format(temperature))

            # Agregar los datos a las listas para el electrocardiograma
            fechas.append(time.strftime('%Y-%m-%d %H:%M:%S'))
            frecuencias_cardiacas.append(int(heart_rate))
            temperaturas.append(float(temperature))

            # Verificar si hay arritmia y mostrar el aviso correspondiente
            if int(heart_rate) > 100:
                label_arrhythmia.config(text="Posible Arritmia", fg="red")
            else:
                label_arrhythmia.config(text="Ritmo Cardíaco Regular", fg="black")

            # Actualizar el electrocardiograma
            ax.clear()
            ax.plot(fechas, frecuencias_cardiacas, color='blue')
            ax.set_xlabel('Fecha y Hora')
            ax.set_ylabel('Frecuencia Cardíaca (BPM)')
            fig.autofmt_xdate()  # Formatear las fechas en el eje x
            fig.tight_layout()  # Ajustar el diseño de la gráfica
            fig.canvas.draw()

    # Llamar a la función nuevamente después de 1 segundo
    root.after(1000, read_sensors)

def consulta_expediente():
    # Crear la ventana de consulta de expediente
    consulta_window = tk.Toplevel()
    consulta_window.title("Consulta de Expediente")
    consulta_window.geometry("600x450")
    consulta_window.configure(bg="lightyellow")

    # Crear un widget Treeview para mostrar los datos de la base de datos
    tree = ttk.Treeview(consulta_window, columns=("Fecha y Hora", "Frecuencia Cardíaca", "Temperatura", "Arritmia"), show="headings")
    tree.heading("Fecha y Hora", text="Fecha y Hora")
    tree.heading("Frecuencia Cardíaca", text="Frecuencia Cardíaca")
    tree.heading("Temperatura", text="Temperatura")
    tree.heading("Arritmia", text="Arritmia")
    tree.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

    # Función para realizar la consulta
    def realizar_consulta():
        try:
            # Borrar las filas existentes en el Treeview
            tree.delete(*tree.get_children())

            # Obtener la fecha ingresada por el usuario
            fecha = entry_fecha.get()

            # Realizar una consulta a la base de datos para obtener los datos de esa fecha
            query = "SELECT fecha_hora, frecuencia_cardiaca, temperatura, arritmia FROM signos_vitales WHERE DATE(fecha_hora) = %s"
            cursor.execute(query, fecha)
            result = cursor.fetchall()

            # Insertar los datos en el Treeview
            for row in result:
                tree.insert("", "end", values=row)
        except Exception as e:
            # Mostrar mensaje de error en caso de excepción
            error_message = "Error en la consulta: " + str(e)
            label_error = tk.Label(consulta_window, text=error_message, font=("Arial", 12, "bold"), bg="white", fg="red")
            label_error.grid(row=2, column=0, padx=10, pady=10, sticky="w")

    # Función para mostrar la gráfica de los datos de la fecha seleccionada
    def mostrar_grafica():
        # Obtener la fecha ingresada por el usuario
        fecha = entry_fecha.get()

        # Realizar una consulta a la base de datos para obtener los datos de esa fecha
        query = "SELECT fecha_hora, frecuencia_cardiaca, temperatura FROM signos_vitales WHERE DATE(fecha_hora) = %s"
        cursor.execute(query, fecha)
        result = cursor.fetchall()

        # Extraer los datos de frecuencia cardíaca y temperatura
        fechas = [row[0] for row in result]
        frecuencias_cardiacas = [row[1] for row in result]
        temperaturas = [row[2] for row in result]

        # Crear una nueva ventana para mostrar la gráfica
        grafica_window = tk.Toplevel()
        grafica_window.title("Gráfica de Signos Vitales")
        grafica_window.geometry("800x600")
        grafica_window.configure(bg="lightpink")

        # Crear una figura y eje para la gráfica
        fig_grafica, ax_grafica = plt.subplots(figsize=(8, 4))

        # Dibujar la gráfica
        ax_grafica.plot(fechas, frecuencias_cardiacas, color='blue')
        ax_grafica.set_xlabel('Fecha y Hora')
        ax_grafica.set_ylabel('Frecuencia Cardíaca (BPM)')
        ax_grafica.set_title('Gráfica de Signos Vitales')
        fig_grafica.autofmt_xdate()  # Formatear las fechas en el eje x
        fig_grafica.tight_layout()  # Ajustar el diseño de la gráfica

        # Crear un lienzo para mostrar la gráfica
        canvas_grafica = FigureCanvasTkAgg(fig_grafica, master=grafica_window)
        canvas_grafica.draw()
        canvas_grafica.get_tk_widget().pack()

        # Función para cerrar la ventana
        def close_window():
            grafica_window.destroy()

        # Botón de cerrar ventana
        button_cerrar = tk.Button(grafica_window, text="Cerrar", font=("Arial", 12), command=close_window)
        button_cerrar.pack(pady=10)

    # Etiqueta y campo de entrada de texto para la fecha
    label_fecha = tk.Label(consulta_window, text="Fecha (YYYY-MM-DD):", font=("Arial", 12), bg="white")
    label_fecha.grid(row=1, column=0, padx=10, pady=5, sticky="e")
    entry_fecha = tk.Entry(consulta_window, font=("Arial", 12))
    entry_fecha.grid(row=1, column=1, padx=10, pady=5, sticky="w")

    # Botón de realizar consulta
    button_consultar = tk.Button(consulta_window, text="Realizar consulta", font=("Arial", 12), command=realizar_consulta)
    button_consultar.grid(row=1, column=2, padx=10, pady=5)

    # Botón de mostrar gráfica
    button_mostrar_grafica = tk.Button(consulta_window, text="Mostrar gráfica", font=("Arial", 12), command=mostrar_grafica)
    button_mostrar_grafica.grid(row=1, column=3, padx=10, pady=5)

def login():
    # Verificar las credenciales de inicio de sesión
    username = entry_username.get()
    password = entry_password.get()

    # Aquí puedes realizar la verificación con tus criterios de autenticación
    if username == "admin" and password == "123456":
        # Destruir la ventana de inicio de sesión
        root.destroy()

        # Crear la ventana de los signos vitales
        global vital_signs_window
        vital_signs_window = tk.Tk()
        vital_signs_window.title("Signos Vitales")
        vital_signs_window.geometry(f"{screen_width}x{screen_height}")
        vital_signs_window.configure(bg="lightgreen")

        # Etiqueta de frecuencia cardíaca
        global label_heart_rate
        label_heart_rate = tk.Label(vital_signs_window, text="Frecuencia Cardíaca:", font=("Arial", 12), bg="white")
        label_heart_rate.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Etiqueta de temperatura
        global label_temperature
        label_temperature = tk.Label(vital_signs_window, text="Temperatura:", font=("Arial", 12), bg="white")
        label_temperature.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        # Etiqueta de arritmia
        global label_arrhythmia
        label_arrhythmia = tk.Label(vital_signs_window, text="", font=("Arial", 12), bg="white")
        label_arrhythmia.grid(row=2, column=0, padx=10, pady=10, sticky="w")

        # Figura y eje para el electrocardiograma
        canvas = FigureCanvasTkAgg(fig, master=vital_signs_window)
        canvas.draw()
        canvas.get_tk_widget().grid(row=3, column=0, padx=10, pady=10, sticky="nsew")

        # Botón de consulta de expediente
        button_consultar = tk.Button(vital_signs_window, text="Consultar expediente", font=("Arial", 12), command=consulta_expediente)
        button_consultar.grid(row=4, column=0, padx=10, pady=10, sticky="w")

        # Iniciar la lectura de los sensores
        read_sensors()

        # Cerrar la conexión a la base de datos al salir de la aplicación
        def close_application():
            connection.close()
            vital_signs_window.destroy()
            root.destroy()

        vital_signs_window.protocol("WM_DELETE_WINDOW", close_application)

        # Ejecución de la ventana de los signos vitales
        vital_signs_window.mainloop()
    else:
        # Mostrar mensaje de error en caso de credenciales incorrectas
        label_error = tk.Label(root, text="Credenciales incorrectas", font=("Arial", 12, "bold"), bg="white", fg="red")
        label_error.pack()

# Crear la ventana principal
root = tk.Tk()
root.title("Inicio de Sesión")
root.geometry(f"{screen_width}x{screen_height}")
root.configure(bg="lightblue")

# Etiquetas, entradas de texto y botón de inicio de sesión
label_username = tk.Label(root, text="Usuario:", font=("Arial", 12), bg="white")
label_username.grid(row=0, column=0, padx=10, pady=10, sticky="e")
entry_username = tk.Entry(root, font=("Arial", 12))
entry_username.grid(row=0, column=1, padx=10, pady=10, sticky="w")
label_password = tk.Label(root, text="Contraseña:", font=("Arial", 12), bg="white")
label_password.grid(row=1, column=0, padx=10, pady=10, sticky="e")
entry_password = tk.Entry(root, show="*", font=("Arial", 12))
entry_password.grid(row=1, column=1, padx=10, pady=10, sticky="w")
button_login = tk.Button(root, text="Iniciar sesión", font=("Arial", 12), command=login)
button_login.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

# Ejecución de la ventana principal
root.mainloop()