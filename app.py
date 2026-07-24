import streamlit as st
import pandas as pd
import json
import os
import datetime
import streamlit.components.v1 as components

# ==========================================
# KONFIGURASI APLIKASI
# ==========================================
st.set_page_config(page_title="Jadwal & Hitung Mundur", page_icon="⏳", layout="wide")

DATA_FILE = "jadwal_data.json"
HARI_LIST = ["SENIN", "SELASA", "RABU", "KAMIS", "JUMAT", "SABTU", "MINGGU"]

# ==========================================
# FUNGSI MANAJEMEN DATA
# ==========================================
def default_data():
    return {
        "settings": {
            "start_time": "07:00",
            "period_duration": 35,
            "max_periods": 9,
            "breaks": [
                {"after_period": 3, "duration": 30, "name": "Istirahat 1"},
                {"after_period": 7, "duration": 65, "name": "Istirahat 2"}
            ]
        },
        "schedule": {
            hari: {str(i): {"mapel": "Kosong", "status": "KOSONG"} for i in range(1, 10)}
            for hari in HARI_LIST
        }
    }

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return default_data()

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

if "app_data" not in st.session_state:
    st.session_state.app_data = load_data()

def get_now_wib():
    # Use timezone-aware datetime for WIB (Waktu Indonesia Barat)
    timezone_wib = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(timezone_wib)

def get_today_name():
    today = get_now_wib().strftime("%A")
    days_map = {
        "Monday": "SENIN", "Tuesday": "SELASA", "Wednesday": "RABU",
        "Thursday": "KAMIS", "Friday": "JUMAT", "Saturday": "SABTU", "Sunday": "MINGGU"
    }
    return days_map.get(today, "SENIN")

# ==========================================
# FUNGSI PERHITUNGAN WAKTU
# ==========================================
def calculate_timeline(settings, hari):
    schedule = st.session_state.app_data["schedule"].get(hari, {})
    
    start_dt = datetime.datetime.strptime(settings["start_time"], "%H:%M")
    current_time = start_dt
    
    blocks = []
    
    # Map break settings for quick lookup
    break_map = {b["after_period"]: b for b in settings["breaks"]}
    
    current_combined_block = None
    
    for i in range(1, settings["max_periods"] + 1):
        period_str = str(i)
        
        # Ambil data pelajaran (jika belum diisi, anggap Kosong)
        pelajaran = schedule.get(period_str, {"mapel": "Kosong", "status": "KOSONG"})
        mapel = pelajaran["mapel"]
        status = pelajaran["status"]
        
        # Hitung waktu mulai dan selesai untuk jam ini
        p_start = current_time.time()
        current_time += datetime.timedelta(minutes=settings["period_duration"])
        p_end = current_time.time()
        
        # Logika Penggabungan Jam Pelajaran (Merge)
        if current_combined_block is None:
            current_combined_block = {
                "start": p_start,
                "end": p_end,
                "mapel": mapel,
                "status": status,
                "jam_ke": [i]
            }
        else:
            if current_combined_block["mapel"] == mapel and current_combined_block["status"] == status:
                # Merge
                current_combined_block["end"] = p_end
                current_combined_block["jam_ke"].append(i)
            else:
                # Simpan blok sebelumnya
                blocks.append(current_combined_block)
                # Mulai blok baru
                current_combined_block = {
                    "start": p_start,
                    "end": p_end,
                    "mapel": mapel,
                    "status": status,
                    "jam_ke": [i]
                }
                
        # Cek apakah ada istirahat setelah jam ini
        if i in break_map:
            # Simpan blok yg sedang berjalan dulu sebelum istirahat
            if current_combined_block is not None:
                blocks.append(current_combined_block)
                current_combined_block = None
                
            b_info = break_map[i]
            b_start = current_time.time()
            current_time += datetime.timedelta(minutes=b_info["duration"])
            b_end = current_time.time()
            
            blocks.append({
                "start": b_start,
                "end": b_end,
                "mapel": b_info.get("name", "Istirahat"),
                "status": "Istirahat",
                "jam_ke": []
            })
            
    if current_combined_block is not None:
        blocks.append(current_combined_block)
        
    return blocks

# ==========================================
# KOMPONEN UI COUNTDOWN JS
# ==========================================
def render_countdown(end_time, title, subtitle):
    now = get_now_wib()
    timezone_wib = datetime.timezone(datetime.timedelta(hours=7))
    end_datetime = datetime.datetime.combine(now.date(), end_time, tzinfo=timezone_wib)
    
    if end_datetime < now:
        end_datetime += datetime.timedelta(days=1)
        
    end_timestamp = int(end_datetime.timestamp() * 1000)
    
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; text-align: center; padding: 40px 20px; background: white; border-radius: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="color: #4E342E; margin-bottom: 10px; font-weight: 800; font-size: 4rem; line-height: 1.2;">{title}</h1>
        <h3 style="color: #757575; margin-top: 0; font-weight: 500; font-size: 1.5rem;">{subtitle}</h3>
        <div id="countdown" style="font-size: 6rem; font-weight: bold; color: #3E2723; margin: 30px 0; letter-spacing: -2px;">-- : -- : --</div>
        <div style="color: #757575; font-size: 1.2rem; font-weight: 500;">
            ⏳ <span id="status">menghitung...</span>
        </div>
    </div>
    
    <script>
        var countDownDate = {end_timestamp};
        
        var x = setInterval(function() {{
            var now = new Date().getTime();
            var distance = countDownDate - now;
            
            if (distance < 0) {{
                clearInterval(x);
                document.getElementById("countdown").innerHTML = "WAKTU HABIS";
                document.getElementById("status").innerHTML = "Memuat ulang...";
                setTimeout(function() {{
                    window.parent.parent.location.reload();
                }}, 2000);
                return;
            }}
            
            var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            var seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            var timeStr = "";
            if (hours > 0) timeStr += hours + " jam ";
            if (minutes > 0 || hours > 0) timeStr += minutes + " menit ";
            timeStr += seconds + " detik";
            
            document.getElementById("countdown").innerHTML = timeStr;
            document.getElementById("status").innerHTML = "lagi menuju waktu habis";
        }}, 1000);
    </script>
    """
    components.html(html, height=450)

# ==========================================
# TAMPILAN UTAMA APLIKASI
# ==========================================
st.title("⏱️ Hitung Mundur Jadwal Mengajar")

tab_utama, tab_jadwal, tab_pengaturan = st.tabs(["⏱️ Hitung Mundur", "📝 Edit Jadwal", "⚙️ Pengaturan & Backup"])

# ------------------------------------------
# TAB 1: HITUNG MUNDUR
# ------------------------------------------
with tab_utama:
    hari_ini = get_today_name()
    idx_hari = HARI_LIST.index(hari_ini) if hari_ini in HARI_LIST else 0
    pilih_hari = st.selectbox("📅 Lihat Jadwal Hari:", HARI_LIST, index=idx_hari)
    
    settings = st.session_state.app_data["settings"]
    blocks = calculate_timeline(settings, pilih_hari)
    
    if not blocks:
        st.warning("Belum ada pengaturan jadwal.")
    else:
        now_time = get_now_wib().time()
        # test_time = st.time_input("Simulasi Jam (Hanya untuk testing)", now_time)
        # now_time = test_time
        
        current_activity = None
        next_activity = None
        
        for i, block in enumerate(blocks):
            if block['start'] <= now_time <= block['end']:
                current_activity = block
                if i + 1 < len(blocks):
                    next_activity = blocks[i+1]
                break
            elif block['start'] > now_time:
                current_activity = {
                    'start': datetime.time(0, 0),
                    'end': block['start'],
                    'status': 'Menunggu',
                    'mapel': 'Belum Mulai',
                    'jam_ke': []
                }
                next_activity = block
                break
                
        if not current_activity:
            st.success("🎉 Seluruh kegiatan hari ini telah selesai!")
            st.balloons()
        else:
            if current_activity['status'] == 'Menunggu':
                st.info(f"Kegiatan selanjutnya akan dimulai pada pukul {current_activity['end'].strftime('%H:%M')}")
                title = f"Menuju: {next_activity['mapel']}"
                if next_activity['jam_ke']:
                    jam_str = ", ".join(str(x) for x in next_activity['jam_ke'])
                    subtitle = f"Jam ke {jam_str} | Mulai: {next_activity['start'].strftime('%H:%M')} - {next_activity['end'].strftime('%H:%M')}"
                else:
                    subtitle = f"Mulai: {next_activity['start'].strftime('%H:%M')} - {next_activity['end'].strftime('%H:%M')}"
                render_countdown(current_activity['end'], title, subtitle)
            else:
                title = current_activity['mapel']
                if current_activity['status'] == 'Istirahat':
                    title = f"☕ {title}"
                elif current_activity['status'] == 'KOSONG':
                    title = f"🆓 {title}"
                else:
                    title = f"📚 {title}"
                
                if current_activity['jam_ke']:
                    jam_str = ", ".join(str(x) for x in current_activity['jam_ke'])
                    subtitle = f"Jam ke {jam_str} | Waktu: {current_activity['start'].strftime('%H:%M')} - {current_activity['end'].strftime('%H:%M')}"
                else:
                    subtitle = f"Waktu: {current_activity['start'].strftime('%H:%M')} - {current_activity['end'].strftime('%H:%M')}"
                render_countdown(current_activity['end'], title, subtitle)
        
        st.markdown("---")
        st.subheader(f"Rincian Jadwal Hari {pilih_hari}")
        display_data = []
        active_index = -1
        for idx, b in enumerate(blocks):
            jam_str = ", ".join(str(x) for x in b['jam_ke']) if b['jam_ke'] else "Istirahat"
            display_data.append({
                "Jam Ke": jam_str,
                "Waktu": f"{b['start'].strftime('%H:%M')} - {b['end'].strftime('%H:%M')}",
                "Status": b['status'],
                "Pelajaran": b['mapel']
            })
            if b['start'] <= now_time <= b['end']:
                active_index = idx
                
        df = pd.DataFrame(display_data)
        
        def highlight_active(row):
            if row.name == active_index:
                return ['background-color: #ffebee; color: #c62828; font-weight: bold'] * len(row)
            return [''] * len(row)
            
        st.table(df.style.apply(highlight_active, axis=1))

# ------------------------------------------
# TAB 2: EDIT JADWAL
# ------------------------------------------
with tab_jadwal:
    st.subheader("📝 Input Jadwal Pelajaran")
    hari_edit = st.selectbox("Pilih Hari yang ingin diedit:", HARI_LIST)
    
    max_p = st.session_state.app_data["settings"]["max_periods"]
    
    # Inisialisasi jika hari ini belum ada di data
    if hari_edit not in st.session_state.app_data["schedule"]:
        st.session_state.app_data["schedule"][hari_edit] = {str(i): {"mapel": "Kosong", "status": "KOSONG"} for i in range(1, max_p + 1)}
    
    # Pastikan jumlah jam sinkron dengan max_periods
    for i in range(1, max_p + 1):
        if str(i) not in st.session_state.app_data["schedule"][hari_edit]:
            st.session_state.app_data["schedule"][hari_edit][str(i)] = {"mapel": "Kosong", "status": "KOSONG"}

    with st.form("form_jadwal"):
        for i in range(1, max_p + 1):
            col1, col2 = st.columns([3, 1])
            curr_mapel = st.session_state.app_data["schedule"][hari_edit][str(i)]["mapel"]
            curr_status = st.session_state.app_data["schedule"][hari_edit][str(i)]["status"]
            
            with col1:
                new_mapel = st.text_input(f"Pelajaran Jam ke-{i}", value=curr_mapel, key=f"mapel_{hari_edit}_{i}")
            with col2:
                new_status = st.selectbox(f"Status", ["Mengajar", "KOSONG"], index=0 if curr_status=="Mengajar" else 1, key=f"status_{hari_edit}_{i}")
            
            # Simpan sementara di session state saat form disubmit nanti
        
        submitted = st.form_submit_button("💾 Simpan Jadwal")
        if submitted:
            for i in range(1, max_p + 1):
                m = st.session_state[f"mapel_{hari_edit}_{i}"]
                s = st.session_state[f"status_{hari_edit}_{i}"]
                st.session_state.app_data["schedule"][hari_edit][str(i)] = {"mapel": m, "status": s}
            
            save_data(st.session_state.app_data)
            st.success("Jadwal berhasil disimpan!")
            st.rerun()

# ------------------------------------------
# TAB 3: PENGATURAN & BACKUP
# ------------------------------------------
with tab_pengaturan:
    st.subheader("⚙️ Pengaturan Waktu Global")
    
    curr_settings = st.session_state.app_data["settings"]
    
    with st.form("form_pengaturan"):
        col_st, col_dur, col_max = st.columns(3)
        with col_st:
            new_start = st.time_input("Jam Mulai Sekolah", datetime.datetime.strptime(curr_settings["start_time"], "%H:%M").time())
        with col_dur:
            new_dur = st.number_input("Durasi per Jam (Menit)", min_value=5, max_value=120, value=curr_settings["period_duration"])
        with col_max:
            new_max = st.number_input("Total Jam Pelajaran / Hari", min_value=1, max_value=15, value=curr_settings["max_periods"])
            
        st.markdown("**Pengaturan Istirahat**")
        # Dinamis render breaks (Untuk kesederhanaan, kita sediakan 3 slot istirahat yg bisa diisi atau dikosongkan)
        breaks_list = curr_settings.get("breaks", [])
        
        new_breaks = []
        for i in range(3):
            col_b1, col_b2, col_b3 = st.columns(3)
            default_b = breaks_list[i] if i < len(breaks_list) else {"after_period": 0, "duration": 0, "name": f"Istirahat {i+1}"}
            
            with col_b1:
                b_name = st.text_input(f"Nama Istirahat {i+1}", value=default_b.get("name", f"Istirahat {i+1}"))
            with col_b2:
                b_after = st.number_input(f"Setelah Jam ke-", min_value=0, max_value=15, value=default_b["after_period"], key=f"bafter_{i}", help="Isi 0 jika tidak digunakan")
            with col_b3:
                b_dur = st.number_input(f"Durasi (Menit)", min_value=0, max_value=120, value=default_b["duration"], key=f"bdur_{i}")
                
            if b_after > 0 and b_dur > 0:
                new_breaks.append({"after_period": b_after, "duration": b_dur, "name": b_name})
        
        btn_simpan_pengaturan = st.form_submit_button("💾 Simpan Pengaturan")
        if btn_simpan_pengaturan:
            st.session_state.app_data["settings"] = {
                "start_time": new_start.strftime("%H:%M"),
                "period_duration": new_dur,
                "max_periods": new_max,
                "breaks": new_breaks
            }
            save_data(st.session_state.app_data)
            st.success("Pengaturan waktu berhasil disimpan!")
            st.rerun()

    st.markdown("---")
    st.subheader("💾 Backup Data (Khusus Web Streamlit)")
    st.info("Karena aplikasi web gratis bisa ter-reset (sleep), silakan Download Data ini secara berkala dan Upload kembali jika data hilang.")
    
    col_d, col_u = st.columns(2)
    with col_d:
        json_string = json.dumps(st.session_state.app_data, indent=4)
        st.download_button(
            label="⬇️ Download Data Backup",
            file_name="jadwal_backup.json",
            mime="application/json",
            data=json_string
        )
    with col_u:
        uploaded_file = st.file_uploader("⬆️ Upload Data Backup", type="json")
        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                if "settings" in data and "schedule" in data:
                    st.session_state.app_data = data
                    save_data(data)
                    st.success("Backup berhasil di-restore!")
                    st.rerun()
                else:
                    st.error("Format file tidak valid.")
            except Exception as e:
                st.error(f"Gagal membaca file: {e}")
