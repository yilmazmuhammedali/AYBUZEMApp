import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os
import io
import time

# --- 1. METİN SÖZLÜĞÜ OLUŞTURMA ---
# Tüm arayüz metinlerini buraya ekliyoruz. Yeni bir dil eklemek için
# sadece bu sözlüğe yeni bir anahtar (örn: 'de' for German) eklemek yeterlidir.
translations = {
    "tr": {
        "app_title": "Grup İçi Akran Değerlendirme Sistemi",
        "language_select_label": "Dil / Language",
        # Yönetici Paneli
        "admin_panel_title": "Yönetici Paneli",
        "admin_logged_in": "Yönetici olarak giriş yapıldı.",
        "refresh_data_button": "Verileri Yenile",
        "all_evaluations_header": "Tüm Değerlendirmeler",
        "admin_password_label": "Yönetici Şifresi:",
        "login_button": "Giriş Yap",
        "wrong_password_error": "Şifre yanlış!",
        # Öğrenci Paneli
        "student_panel_header": "Öğrenci Paneli",
        "student_id_prompt": "Lütfen Öğrenci Numaranızı Girin:",
        "continue_button": "Devam Et",
        "student_not_found_error": "Bu öğrenci numarası sistemde kayıtlı değil.",
        "enter_student_id_warning": "Lütfen bir öğrenci numarası girin.",
        "welcome_message": "Hoş geldin, {name}! ({group})",
        "logout_button": "Başka Öğrenci Olarak Giriş Yap (Çıkış)",
        "already_evaluated_warning": "Bu grup için değerlendirmenizi daha önce tamamlamışsınız. Tekrar değerlendirme yapamazsınız.",
        "no_one_to_evaluate_info": "Grubunuzda değerlendirilecek başka üye bulunmamaktadır.",
        "evaluation_subheader": "Lütfen grup arkadaşlarınızı 1 (En Düşük) ile 10 (En Yüksek) arasında puanlayınız.",
        "comment_label": "Yorum (isteğe bağlı):",
        "comment_placeholder": "{name} hakkındaki yorumlarınız...",
        "submit_button": "Değerlendirmeleri Gönder",
        "evaluation_success_message": "Değerlendirmeleriniz başarıyla kaydedildi!",
        # Sistem Hataları
        "excel_file_error": "Lütfen uygulama klasörüne '{file}' dosyasını ekleyin.",
        "excel_column_error": "Excel dosyasında gerekli sütunlar bulunamadı! Lütfen şu sütunların olduğundan emin olun: {columns}"
    },
    "en": {
        "app_title": "Peer Assessment System for Groups",
        "language_select_label": "Dil / Language",
        # Admin Panel
        "admin_panel_title": "Admin Panel",
        "admin_logged_in": "Logged in as admin.",
        "refresh_data_button": "Refresh Data",
        "all_evaluations_header": "All Evaluations",
        "admin_password_label": "Admin Password:",
        "login_button": "Login",
        "wrong_password_error": "Wrong password!",
        # Student Panel
        "student_panel_header": "Student Panel",
        "student_id_prompt": "Please Enter Your Student ID:",
        "continue_button": "Continue",
        "student_not_found_error": "This student ID is not registered in the system.",
        "enter_student_id_warning": "Please enter a student ID.",
        "welcome_message": "Welcome, {name}! ({group})",
        "logout_button": "Login as Another Student (Logout)",
        "already_evaluated_warning": "You have already completed your evaluation for this group. You cannot evaluate again.",
        "no_one_to_evaluate_info": "There are no other members in your group to evaluate.",
        "evaluation_subheader": "Please rate your group members between 1 (Lowest) and 10 (Highest).",
        "comment_label": "Comment (optional):",
        "comment_placeholder": "Your comments about {name}...",
        "submit_button": "Submit Evaluations",
        "evaluation_success_message": "Your evaluations have been saved successfully!",
        # System Errors
        "excel_file_error": "Please add the '{file}' file to the application folder.",
        "excel_column_error": "Required columns not found in the Excel file! Please ensure the following columns exist: {columns}"
    }
}

# --- Ayarlar ---
DB_FILE = "medicine_survey.sqlite"
ADMIN_PASSWORD = "aybubio2025"
EXCEL_FILE_PATH = r'Groups.xlsx'

# --- Veritabanı Fonksiyonları (Değişiklik yok) ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS ogrenciler (student_no TEXT PRIMARY KEY, fullname TEXT NOT NULL, group_name TEXT NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS degerlendirmeler (id INTEGER PRIMARY KEY AUTOINCREMENT, evaluator_no TEXT NOT NULL, evaluated_no TEXT NOT NULL, puan INTEGER, yorum TEXT, kayit_zamani TEXT)')
    conn.commit()
    conn.close()
    
# --- 4. YARDIMCI FONKSİYON ---
# Bu fonksiyon, seçili dile göre doğru metni döndürecek.
def t(key, **kwargs):
    # Eğer session_state'de dil tanımlı değilse, varsayılan olarak 'tr' kullan
    lang = st.session_state.get('lang', 'tr')
    # Sözlükten metni al ve formatla (örn: {name})
    return translations[lang][key].format(**kwargs)


def load_students_from_excel():
    if os.path.exists(EXCEL_FILE_PATH):
        try:
            df = pd.read_excel(EXCEL_FILE_PATH)
            required_columns = ['student_no', 'fullname', 'group_name']
            if not all(col in df.columns for col in required_columns):
                # Hata mesajını t() fonksiyonu ile alıyoruz
                st.error(t("excel_column_error", columns=required_columns))
                return False
            
            conn = get_db_connection()
            df.to_sql('ogrenciler', conn, if_exists='replace', index=False, dtype={'student_no': 'TEXT'})
            conn.close()
            return True
        except Exception as e:
            st.error(f"Excel file read error: {e}")
            return False
    return False

# Diğer veritabanı fonksiyonları (check_if_evaluated, get_student_info vb.) aynı kalır
def check_if_evaluated(student_no):
    conn = get_db_connection()
    result = conn.execute('SELECT 1 FROM degerlendirmeler WHERE evaluator_no = ? LIMIT 1', (str(student_no),)).fetchone()
    conn.close()
    return result is not None

def get_student_info(student_no):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM ogrenciler WHERE student_no = ?', (str(student_no),)).fetchone()
    conn.close()
    return student

def get_group_members(group_name, exclude_student_no):
    conn = get_db_connection()
    members = conn.execute('SELECT * FROM ogrenciler WHERE group_name = ? AND student_no != ?', (group_name, str(exclude_student_no))).fetchall()
    conn.close()
    return members

def add_evaluation(evaluator_no, evaluated_no, puan, yorum):
    conn = get_db_connection()
    conn.execute('INSERT INTO degerlendirmeler (evaluator_no, evaluated_no, puan, yorum, kayit_zamani) VALUES (?, ?, ?, ?, ?)', (str(evaluator_no), str(evaluated_no), puan, yorum, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_all_evaluations():
    conn = get_db_connection()
    query = "SELECT d.evaluator_no, o1.fullname as evaluator_name, d.evaluated_no, o2.fullname as evaluated_name, o2.group_name, d.puan, d.yorum, d.kayit_zamani FROM degerlendirmeler d LEFT JOIN ogrenciler o1 ON d.evaluator_no = o1.student_no LEFT JOIN ogrenciler o2 ON d.evaluated_no = o2.student_no"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- Uygulama Başlangıcı ---
init_db()
if 'students_loaded' not in st.session_state:
    if load_students_from_excel():
        st.session_state.students_loaded = True
    else:
        st.error(t("excel_file_error", file=EXCEL_FILE_PATH))
        st.stop()

# --- Streamlit Arayüzü ---
st.set_page_config(layout="wide")

# --- 3. DİL SEÇİMİ VE DURUM YÖNETİMİ ---
# Varsayılan dil 'tr' olarak ayarlanır
if 'lang' not in st.session_state:
    st.session_state.lang = 'tr'

# Arayüzdeki tüm metinler artık t() fonksiyonu ile çağrılıyor
st.title(t("app_title"))

if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'student_info' not in st.session_state:
    st.session_state.student_info = None

# --- Yönetici ve Dil Seçim Paneli ---
with st.sidebar:
    # Dil seçimi selectbox'ı
    selected_lang = st.selectbox(
        label=t('language_select_label'), 
        options=['tr', 'en'], 
        format_func=lambda x: "Türkçe" if x == 'tr' else "English",
        key='lang' # session_state ile doğrudan bağlantı
    )

    st.title(t("admin_panel_title"))
    if st.session_state.admin_authenticated:
        st.success(t("admin_logged_in"))
        
        if st.button(t("refresh_data_button")):
            st.rerun()

        st.header(t("all_evaluations_header"))
        all_evaluations = get_all_evaluations()
        st.dataframe(all_evaluations)
    else:
        password = st.text_input(t("admin_password_label"), type="password")
        if st.button(t("login_button")):
            if password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error(t("wrong_password_error"))

# --- Öğrenci Paneli ---
st.header(t("student_panel_header"))

if st.session_state.student_info is None:
    student_no_input = st.text_input(t("student_id_prompt"), key="student_login_input")
    if st.button(t("continue_button")):
        if student_no_input:
            student = get_student_info(student_no_input)
            if student:
                st.session_state.student_info = dict(student)
                st.rerun()
            else:
                st.error(t("student_not_found_error"))
        else:
            st.warning(t("enter_student_id_warning"))
else:
    student = st.session_state.student_info
    st.success(t("welcome_message", name=student['fullname'], group=student['group_name']))
    
    if st.button(t("logout_button")):
        st.session_state.student_info = None
        st.rerun()

    has_evaluated = check_if_evaluated(student['student_no'])

    if has_evaluated:
        st.warning(t("already_evaluated_warning"))
    else:
        group_members = get_group_members(student['group_name'], student['student_no'])

        if not group_members:
            st.info(t("no_one_to_evaluate_info"))
        else:
            with st.form("degerlendirme_formu"):
                st.subheader(t("evaluation_subheader"))
                
                for member in group_members:
                    st.markdown("---")
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.markdown(f"#### {member['fullname']}")
                        st.caption(f"({member['student_no']})")

                    with col2:
                        puan_key = f"puan_{member['student_no']}"
                        yorum_key = f"yorum_{member['student_no']}"
                        
                        st.radio(
                            "Puan:",
                            options=list(range(1, 11)),
                            key=puan_key,
                            horizontal=True,
                            label_visibility="collapsed"
                        )
                        
                        st.text_area(
                            t("comment_label"),
                            key=yorum_key,
                            placeholder=t("comment_placeholder", name=member['fullname'])
                        )
                
                submitted = st.form_submit_button(t("submit_button"))

                if submitted:
                    for member in group_members:
                        puan = st.session_state[f"puan_{member['student_no']}"]
                        yorum = st.session_state[f"yorum_{member['student_no']}"]
                        add_evaluation(
                            evaluator_no=student['student_no'],
                            evaluated_no=member['student_no'],
                            puan=puan,
                            yorum=yorum
                        )
                    st.success(t("evaluation_success_message"))
                    st.balloons()
                    time.sleep(2)
                    st.rerun()