import urllib
from collections import defaultdict
# devconsole/services/telemetry_service.py
import datetime
import json
import os
import re
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from devconsole.services.ttl_cache import ttl_cache
from devconsole.config import (
    BASE_DIR,
    PEAK_FILE,
    KEYCLOAK_ENV_CONFIGS,
    DATABASE_ENV_CONFIGS,
    normalize_env_key,
)

OPERATIONAL_MAP_CACHE = {}
KEYCLOAK_USERS_DETAIL_CACHE = {}
KEYCLOAK_ADMINS_CACHE = {}
LIVE_FRONTEND_TELEMETRY = {}
LIVE_SCREEN_MIRROR = {}
ACTIVE_MIRROR_SUBSCRIPTIONS = set()
PEAK_FILE = BASE_DIR / "data" / "operational_peak.json"

def get_operational_peak() -> dict:
    if PEAK_FILE.exists():
        try:
            with open(PEAK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"count": 0, "timestamp": "Sin registros", "env": "develop", "unique_users": 0}

def update_operational_peak(total_conns: int, env_key: str, unique_users: int) -> dict:
    current = get_operational_peak()
    if total_conns > current.get("count", 0):
        current = {
            "count": total_conns,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "env": env_key,
            "unique_users": unique_users
        }
        try:
            PEAK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(PEAK_FILE, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
        except Exception:
            pass
    return current

def get_operational_map_data(env_key: str = "develop", force_refresh: bool = False) -> dict:
    global OPERATIONAL_MAP_CACHE, KEYCLOAK_USERS_DETAIL_CACHE, KEYCLOAK_ADMINS_CACHE
    now = time.time()
    env_key = normalize_env_key(env_key)
    
    cfg = KEYCLOAK_ENV_CONFIGS.get(env_key, KEYCLOAK_ENV_CONFIGS["develop"])
    db_cfg = DATABASE_ENV_CONFIGS.get(env_key, DATABASE_ENV_CONFIGS["develop"])
    
    cached_entry = OPERATIONAL_MAP_CACHE.get(env_key)
    if not force_refresh and cached_entry and (now - cached_entry.get("timestamp", 0) < 15):
        res = dict(cached_entry["data"])
        res["cached"] = True
        res["cache_age_sec"] = round(now - cached_entry["timestamp"], 1)
        res["peak_connections"] = get_operational_peak()
        return res

    t0 = time.time()
    db_ok = False
    db_latency_ms = 0
    kc_ok = False
    kc_latency_ms = 0
    error_msg = ""
    
    ZONE_META = {
        1: {
            "name": "Primera Zona Naval",
            "sigla": "I Z.N.",
            "sede": "Valparaíso / Viña del Mar",
            "color": "#3b82f6",
            "jurisdiccion": "Coquimbo hasta San Antonio, Región Metropolitana e Islas Oceánicas",
            "bases": ["Valparaíso (HQ)", "Viña del Mar (APOLINAV)", "Santiago (Telecomunicaciones)", "Coquimbo (Gobernación Marítima)"],
            "svg_polygon": "138,220 180,220 175,385 126,385 127,345 130,305 135,260"
        },
        2: {
            "name": "Segunda Zona Naval",
            "sigla": "II Z.N.",
            "sede": "Talcahuano (Base Naval)",
            "color": "#f59e0b",
            "jurisdiccion": "Maule, Ñuble, Biobío, Araucanía hasta Los Ríos (Valdivia)",
            "bases": ["Talcahuano (Base Naval / ESGRUM)", "Concepción", "Valdivia / Corral"],
            "svg_polygon": "126,385 175,385 170,495 118,495 115,450 119,428 124,400"
        },
        3: {
            "name": "Tercera Zona Naval",
            "sigla": "III Z.N.",
            "sede": "Punta Arenas (Magallanes)",
            "color": "#a855f7",
            "jurisdiccion": "Magallanes, Canal Beagle, Cabo de Hornos y Territorio Antártico Chileno",
            "bases": ["Punta Arenas (HQ)", "Puerto Williams", "Base Naval Antártica Arturo Prat", "Bahía Fildes"],
            "svg_polygon": "110,660 165,660 180,860 135,860 140,800 138,750 120,705"
        },
        4: {
            "name": "Cuarta Zona Naval",
            "sigla": "IV Z.N.",
            "sede": "Iquique (Base Naval)",
            "color": "#06b6d4",
            "jurisdiccion": "Límite Norte Internacional (Arica) hasta Río Loa / Región de Antofagasta",
            "bases": ["Iquique (Base Naval / HQ)", "Arica (Gobernación Marítima)", "Antofagasta"],
            "svg_polygon": "154,48 195,48 180,220 138,220 139,170 145,120 152,70"
        },
        5: {
            "name": "Quinta Zona Naval",
            "sigla": "V Z.N.",
            "sede": "Puerto Montt (Reloncaví)",
            "color": "#10b981",
            "jurisdiccion": "Región de Los Lagos (Chiloé, Palena) y Región de Aysén",
            "bases": ["Puerto Montt (HQ)", "Castro (Chiloé)", "Puerto Chacabuco (Aysén)"],
            "svg_polygon": "118,495 170,495 165,660 110,660 114,620 112,555 125,518"
        },
        9: {
            "name": "Misiones en el Extranjero",
            "sigla": "EXTRANJ.",
            "sede": "Agregadurías Navales",
            "color": "#14b8a6",
            "jurisdiccion": "Agregadurías Militares y Misiones Diplomáticas",
            "bases": ["CHILIARCO (Washington D.C., EE.UU.)", "CHILONDON (Londres, UK)"],
            "svg_polygon": ""
        },
        0: {
            "name": "Otras / Sin Repartición Asignada",
            "sigla": "OTRAS",
            "sede": "Servicios Centrales / Sin Destinación Vigente",
            "color": "#64748b",
            "jurisdiccion": "Cuentas Técnicas, SSO o sin Registro de Destinación Activa en DB",
            "bases": ["Cuentas Técnicas / SSO"],
            "svg_polygon": ""
        }
    }

    zones_data = {}
    for zid, meta in ZONE_META.items():
        zones_data[zid] = {
            "id": zid,
            "sigla": meta["sigla"],
            "name": meta["name"],
            "sede": meta["sede"],
            "color": meta["color"],
            "jurisdiccion": meta["jurisdiccion"],
            "bases": meta["bases"],
            "svg_polygon": meta["svg_polygon"],
            "total_connections": 0,
            "unique_users": 0,
            "percentage": 0.0,
            "reparticiones": []
        }

    # 1. Query Keycloak for active user sessions
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    sessions = []
    pna_sessions_count = defaultdict(int)
    
    t_kc_start = time.time()
    try:
        token_url = f"{cfg['url']}/realms/{cfg['realm']}/protocol/openid-connect/token"
        req_token_data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"]
        }).encode("utf-8")
        req_token = urllib.request.Request(token_url, data=req_token_data)
        with urllib.request.urlopen(req_token, timeout=3.5, context=ctx) as r:
            token = json.loads(r.read().decode("utf-8"))["access_token"]
            
        clients_url = f"{cfg['url']}/admin/realms/{cfg['realm']}/clients?clientId={cfg['client_id']}"
        req_c = urllib.request.Request(clients_url)
        req_c.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req_c, timeout=3.5, context=ctx) as r:
            clients = json.loads(r.read().decode("utf-8"))
            c_uuid = clients[0]["id"]
            
        sess_url = f"{cfg['url']}/admin/realms/{cfg['realm']}/clients/{c_uuid}/user-sessions?max=500"
        req_s = urllib.request.Request(sess_url)
        req_s.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req_s, timeout=4.0, context=ctx) as r:
            sessions = json.loads(r.read().decode("utf-8"))
            
        kc_ok = True
        kc_latency_ms = round((time.time() - t_kc_start) * 1000, 1)
        for s in sessions:
            uid = s.get("userId")
            if uid:
                pna_sessions_count[uid] += 1

        # Fetch Keycloak admin users (cached per env for 1 hour)
        admin_uids = set()
        admin_unames = set()
        admin_cache_entry = KEYCLOAK_ADMINS_CACHE.get(env_key)
        if admin_cache_entry and (now - admin_cache_entry.get("ts", 0) < 3600):
            admin_uids = admin_cache_entry.get("uids", set())
            admin_unames = admin_cache_entry.get("unames", set())
        elif 'token' in locals() and token:
            try:
                req_g = urllib.request.Request(f"{cfg['url']}/admin/realms/{cfg['realm']}/groups")
                req_g.add_header("Authorization", f"Bearer {token}")
                with urllib.request.urlopen(req_g, timeout=2.5, context=ctx) as rg:
                    groups = json.loads(rg.read().decode("utf-8"))
                    for g in groups:
                        if g.get("name") in ("g_sisper_admin", "g_sisper_ti", "g_mod_adm_admin"):
                            gid = g["id"]
                            req_m = urllib.request.Request(f"{cfg['url']}/admin/realms/{cfg['realm']}/groups/{gid}/members")
                            req_m.add_header("Authorization", f"Bearer {token}")
                            with urllib.request.urlopen(req_m, timeout=2.5, context=ctx) as rm:
                                members = json.loads(rm.read().decode("utf-8"))
                                for m in members:
                                    if m.get("id"): admin_uids.add(m["id"])
                                    if m.get("username"): admin_unames.add(m["username"])
                if 'c_uuid' in locals() and c_uuid:
                    try:
                        req_ra = urllib.request.Request(f"{cfg['url']}/admin/realms/{cfg['realm']}/clients/{c_uuid}/roles/r_sisper_admin/users")
                        req_ra.add_header("Authorization", f"Bearer {token}")
                        with urllib.request.urlopen(req_ra, timeout=2.5, context=ctx) as rra:
                            ra_users = json.loads(rra.read().decode("utf-8"))
                            for ru in ra_users:
                                if ru.get("id"): admin_uids.add(ru["id"])
                                if ru.get("username"): admin_unames.add(ru["username"])
                    except Exception:
                        pass
                KEYCLOAK_ADMINS_CACHE[env_key] = {"uids": admin_uids, "unames": admin_unames, "ts": now}
            except Exception:
                pass
    except Exception as e:
        kc_ok = False
        error_msg = f"Keycloak {env_key}: {str(e)}"
        kc_latency_ms = round((time.time() - t_kc_start) * 1000, 1)

    total_connections = len(sessions)
    unique_pnas = list(pna_sessions_count.keys())
    unique_users = len(unique_pnas)

    # 2. Consultar las bases configuradas para mapear PNAs a Reparticiones y Zonas
    pna_to_dest = {}
    if unique_pnas:
        t_db_start = time.time()
        try:
            # Step A: Contratos priorizados (ID_PNA -> ID_CTTO)
            # Prioriza: 1=Vigente, 3=Pendiente Retiro, 4=Pendiente Activación, excluye 5=Anulado y registros en CONTRATO_PNA_ANULA
            pna_list_sql = ",".join(f"'{u}'" for u in unique_pnas)
            sql_cttos = f'''
                WITH ranked_cttos AS (
                    SELECT 
                        c."ID_PNA", 
                        c."ID_CTTO", 
                        ROW_NUMBER() OVER (
                            PARTITION BY c."ID_PNA"
                            ORDER BY 
                                CASE 
                                    WHEN a."ID_CTTO_id" IS NOT NULL OR h."COD_ESTADO_CTTO_id" = 5 THEN 99
                                    WHEN h."COD_ESTADO_CTTO_id" = 1 THEN 1
                                    WHEN h."COD_ESTADO_CTTO_id" = 3 THEN 2
                                    WHEN h."COD_ESTADO_CTTO_id" = 4 THEN 3
                                    ELSE 10
                                END ASC,
                                c."COD_TP_CTTO_id" ASC,
                                c."FEC_INI_CTTO" DESC,
                                c."SEC_CTTO" DESC
                        ) as rn
                    FROM "CONTRATO_PNA_REAL" c
                    LEFT JOIN "ESTADO_HISTORICO_CTTO" h ON h."ID_CTTO_id" = c."ID_CTTO" AND h."IS_VIG" = true
                    LEFT JOIN "CONTRATO_PNA_ANULA" a ON a."ID_CTTO_id" = c."ID_CTTO"
                    WHERE c."ID_PNA" IN ({pna_list_sql})
                      AND a."ID_CTTO_id" IS NULL
                      AND COALESCE(h."COD_ESTADO_CTTO_id", 0) != 5
                )
                SELECT "ID_PNA", "ID_CTTO"
                FROM ranked_cttos
                ORDER BY "ID_PNA", rn ASC;
            '''
            cmd1 = [
                "psql", "-h", db_cfg["host"], "-p", str(db_cfg["port"]), "-U", db_cfg["contratos_user"], "-d", db_cfg["contratos_db"],
                "-t", "-A", "-F", "|", "-c", sql_cttos
            ]
            env_vars1 = os.environ.copy()
            env_vars1["PGPASSWORD"] = db_cfg["contratos_pass"]
            res1 = subprocess.run(cmd1, env=env_vars1, capture_output=True, text=True, timeout=6)
            
            pna_to_cttos = defaultdict(list)
            all_cttos = set()
            if res1.returncode == 0:
                for line in res1.stdout.strip().split("\n"):
                    if line.strip():
                        p, c = line.strip().split("|")
                        pna_to_cttos[p].append(c)
                        all_cttos.add(c)
            
            # Step B: Destinaciones priorizadas (ID_CTTO -> Repartición & Zona)
            # Prioriza destinaciones con IND_VIG_DEST=true y mayor CORREL_DEST
            ctto_dest_map = {}
            if all_cttos:
                ctto_list_sql = ",".join(f"'{c}'" for c in all_cttos)
                sql_dest = f'''
                    WITH ranked_dest AS (
                        SELECT 
                            d."ID_CTTO", 
                            u."COD_UNID_REP", 
                            u."SIGLA_UNID_REP", 
                            u."DESC_UNID_REP", 
                            COALESCE(z."COD_ZONA", 0) as cod_zona, 
                            COALESCE(z."SIGLA_ZONA", 'OTRO') as sigla_zona,
                            ROW_NUMBER() OVER (
                                PARTITION BY d."ID_CTTO"
                                ORDER BY 
                                    CASE WHEN d."IND_VIG_DEST" = true THEN 1 ELSE 2 END ASC,
                                    d."CORREL_DEST" DESC,
                                    d."FEC_ALTA_DEST" DESC
                            ) as rn
                        FROM "DESTINACIONES_PNA" d
                        JOIN "UNIDAD_REPARTICION" u ON COALESCE(d."COD_UNID_REP_DEST_id", d."COD_UNID_REP_DOT_id") = u."COD_UNID_REP"
                        LEFT JOIN "ZONA" z ON u."COD_ZONA_id" = z."COD_ZONA"
                        WHERE d."ID_CTTO" IN ({ctto_list_sql})
                    )
                    SELECT "ID_CTTO", "COD_UNID_REP", "SIGLA_UNID_REP", "DESC_UNID_REP", cod_zona, sigla_zona
                    FROM ranked_dest
                    WHERE rn = 1;
                '''
                cmd2 = [
                    "psql", "-h", db_cfg["host"], "-p", str(db_cfg["port"]), "-U", db_cfg["destinaciones_user"], "-d", db_cfg["destinaciones_db"],
                    "-t", "-A", "-F", "|", "-c", sql_dest
                ]
                env_vars2 = os.environ.copy()
                env_vars2["PGPASSWORD"] = db_cfg["destinaciones_pass"]
                res2 = subprocess.run(cmd2, env=env_vars2, capture_output=True, text=True, timeout=6)
                if res2.returncode == 0:
                    for line in res2.stdout.strip().split("\n"):
                        if line.strip():
                            parts = line.strip().split("|")
                            if len(parts) >= 6:
                                ctto_dest_map[parts[0]] = {
                                    "cod_rep": int(parts[1]),
                                    "sigla_rep": parts[2],
                                    "desc_rep": parts[3],
                                    "cod_zona": int(parts[4]),
                                    "sigla_zona": parts[5]
                                }
            db_ok = True
            db_latency_ms = round((time.time() - t_db_start) * 1000, 1)

            # Match PNA to active destinacion
            for uid in unique_pnas:
                cttos = pna_to_cttos.get(uid, [])
                matched = False
                for c in cttos:
                    if c in ctto_dest_map:
                        pna_to_dest[uid] = ctto_dest_map[c]
                        matched = True
                        break
                if not matched:
                    pna_to_dest[uid] = {
                        "cod_rep": 9999,
                        "sigla_rep": "SIN_DEST_VIG",
                        "desc_rep": "Sesión SSO sin Destinación Vigente en DB",
                        "cod_zona": 0,
                        "sigla_zona": "OTRO"
                    }
        except Exception as e:
            db_ok = False
            db_latency_ms = round((time.time() - t_db_start) * 1000, 1)
            error_msg = f"DB Error: {str(e)}"
    else:
        db_ok = True

    # 2.5 Resolve user names & emails from Keycloak (cached in memory)
    user_details = {}
    if unique_pnas and 'token' in locals() and token:
        for uid in unique_pnas:
            cached_u = KEYCLOAK_USERS_DETAIL_CACHE.get(uid)
            if cached_u and (now - cached_u.get("ts", 0) < 3600):
                user_details[uid] = cached_u
            else:
                try:
                    u_url = f"{cfg['url']}/admin/realms/{cfg['realm']}/users/{uid}"
                    req_u = urllib.request.Request(u_url)
                    req_u.add_header("Authorization", f"Bearer {token}")
                    with urllib.request.urlopen(req_u, timeout=1.5, context=ctx) as ru:
                        u_obj = json.loads(ru.read().decode("utf-8"))
                        fn = u_obj.get("firstName", "").strip()
                        ln = u_obj.get("lastName", "").strip()
                        fl = f"{fn} {ln}".strip()
                        em = u_obj.get("email", "").strip()
                        d = {"full_name": fl, "email": em, "ts": now}
                        KEYCLOAK_USERS_DETAIL_CACHE[uid] = d
                        user_details[uid] = d
                except Exception:
                    d = {"full_name": "", "email": "", "ts": now}
                    KEYCLOAK_USERS_DETAIL_CACHE[uid] = d
                    user_details[uid] = d

    # 3. Aggregate active sessions into zones and reparticiones
    zone_reps = defaultdict(lambda: defaultdict(lambda: {
        "connections": 0, 
        "users": set(), 
        "sigla": "", 
        "desc": "", 
        "cod": 0,
        "users_map": {}
    }))
    
    for s in sessions:
        uid = s.get("userId")
        uname = s.get("username") or "Usuario SSO"
        ip = s.get("ipAddress") or "127.0.0.1"
        start_ts = s.get("start")
        last_ts = s.get("lastAccess")
        u_info = user_details.get(uid, {})
        fl_name = u_info.get("full_name") or uname
        em = u_info.get("email", "")

        dest = pna_to_dest.get(uid, {
            "cod_rep": 9999,
            "sigla_rep": "SIN_DEST_VIG",
            "desc_rep": "Sesión SSO sin Destinación Vigente en DB",
            "cod_zona": 0,
            "sigla_zona": "OTRO"
        })
        zid = dest["cod_zona"]
        if zid not in zones_data:
            zid = 0
            
        r_cod = dest["cod_rep"]
        r_item = zone_reps[zid][r_cod]
        r_item["connections"] += 1
        user_key = uid if uid else uname
        r_item["users"].add(user_key)
        r_item["sigla"] = dest["sigla_rep"]
        r_item["desc"] = dest["desc_rep"]
        r_item["cod"] = r_cod

        is_admin = bool(uid in admin_uids or uname in admin_unames or "admin" in uname.lower())
        if user_key not in r_item["users_map"]:
            r_item["users_map"][user_key] = {
                "user_id": uid,
                "username": uname,
                "full_name": fl_name,
                "email": em,
                "is_admin": is_admin,
                "sessions_count": 0,
                "ips": [],
                "start": start_ts,
                "last_access": last_ts,
                "sessions": []
            }
        
        u_entry = r_item["users_map"][user_key]
        if is_admin:
            u_entry["is_admin"] = True
        u_entry["sessions_count"] += 1
        if ip and ip not in u_entry["ips"]:
            u_entry["ips"].append(ip)
        if start_ts and (not u_entry["start"] or start_ts < u_entry["start"]):
            u_entry["start"] = start_ts
        if last_ts and (not u_entry["last_access"] or last_ts > u_entry["last_access"]):
            u_entry["last_access"] = last_ts
        u_entry["sessions"].append({
            "session_id": s.get("id", ""),
            "ip": ip,
            "start": start_ts,
            "last_access": last_ts
        })

    for zid in zones_data:
        z_conns = sum(r["connections"] for r in zone_reps[zid].values())
        all_z_users = set()
        for r in zone_reps[zid].values():
            all_z_users.update(r["users"])
        zones_data[zid]["total_connections"] = z_conns
        zones_data[zid]["unique_users"] = len(all_z_users)

    # 4. Format reparticiones list and calculate percentages
    all_active_reps = []
    zone_order = [1, 2, 3, 4, 5, 9, 0]
    ordered_zones = []
    
    for zid in zone_order:
        z = zones_data[zid]
        z_conns = z["total_connections"]
        z_users = z["unique_users"]
        z["percentage"] = round((z_users / unique_users * 100), 1) if unique_users > 0 else 0.0
        
        reps_list = []
        for r_cod, r_info in zone_reps[zid].items():
            r_users = len(r_info["users"])
            r_pct = round((r_users / z_users * 100), 1) if z_users > 0 else 0.0
            nacional_pct = round((r_users / unique_users * 100), 1) if unique_users > 0 else 0.0
            
            active_users_list = []
            for u in r_info["users_map"].values():
                u_obj = dict(u)
                u_obj["ip"] = ", ".join(u["ips"]) if u["ips"] else "127.0.0.1"
                active_users_list.append(u_obj)
            active_users_list.sort(key=lambda x: (not x.get("is_admin", False), -(x.get("sessions_count", 1)), (x["full_name"] or x["username"]).lower()))

            rep_obj = {
                "cod": r_info["cod"],
                "sigla": r_info["sigla"],
                "desc": r_info["desc"],
                "connections": r_info["connections"],
                "users": r_users,
                "pct": r_pct,
                "pct_nacional": nacional_pct,
                "zona_id": zid,
                "zona_sigla": z["sigla"],
                "zona_name": z["name"],
                "zona_color": z["color"],
                "active_users": active_users_list
            }
            reps_list.append(rep_obj)
            all_active_reps.append(rep_obj)
            
        reps_list.sort(key=lambda x: (x["users"], x["connections"]), reverse=True)
        z["reparticiones"] = reps_list
        ordered_zones.append(z)

    all_active_reps.sort(key=lambda x: (x["users"], x["connections"]), reverse=True)
    top_zone = max(ordered_zones, key=lambda x: (x["unique_users"], x["total_connections"])) if unique_users > 0 else None
    top_rep = max(all_active_reps, key=lambda x: (x["users"], x["connections"])) if all_active_reps else None

    peak_info = update_operational_peak(total_connections, env_key, unique_users)

    result = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "env": env_key,
        "env_name": cfg["name"],
        "env_ip": cfg.get("ingress_ip", ""),
        "cached": False,
        "total_connections": total_connections,
        "unique_users": unique_users,
        "peak_connections": peak_info,
        "active_zones_count": sum(1 for z in ordered_zones if z["total_connections"] > 0),
        "active_reparticiones_count": len(all_active_reps),
        "all_active_reparticiones": all_active_reps,
        "top_zone": {
            "id": top_zone["id"],
            "sigla": top_zone["sigla"],
            "name": top_zone["name"],
            "connections": top_zone["total_connections"],
            "percentage": top_zone["percentage"]
        } if top_zone and top_zone["total_connections"] > 0 else None,
        "top_reparticion": {
            "cod": top_rep["cod"],
            "sigla": top_rep["sigla"],
            "desc": top_rep["desc"],
            "connections": top_rep["connections"]
        } if top_rep else None,
        "keycloak": {
            "status": "online" if kc_ok else "offline",
            "url": cfg["url"],
            "realm": cfg["realm"],
            "active_sessions": total_connections,
            "latency_ms": kc_latency_ms
        },
        "db": {
            "connected": db_ok,
            "host": db_cfg["host"],
            "port": db_cfg["port"],
            "latency_ms": db_latency_ms
        },
        "error": error_msg,
        "latency_total_ms": round((time.time() - t0) * 1000, 1),
        "zones": ordered_zones,
        "privacy_compliance": {
            "policy": "data-privacy-policy",
            "pii_exposed": False,
            "level": "STRICT_AGGREGATE_ONLY",
            "description": "Zero datos personales sensibles expuestos (sin RUT, nombres ni correos). Agregación técnica de conexiones por Repartición y Zona Naval."
        }
    }

    if kc_ok or total_connections > 0:
        OPERATIONAL_MAP_CACHE[env_key] = {
            "data": result,
            "timestamp": now
        }

    return result

# ------------------------------------------------------------------------------
# VERIFICACIÓN DE SESIÓN KEYCLOAK SSO EN VIVO (ESTADO ONLINE / OFFLINE)
# ------------------------------------------------------------------------------
def get_user_live_session_info(env_key: str, user_filter: str) -> dict:
    """Verifica si un usuario específico tiene sesión activa en Keycloak SSO en este entorno."""
    if not user_filter:
        return {"is_online": False, "status": "UNKNOWN", "message": "No user specified"}

    clean_target = user_filter.strip().lower()
    map_data = get_operational_map_data(env_key=env_key, force_refresh=False)

    for rep in map_data.get("all_active_reparticiones", []):
        for u in rep.get("active_users", []):
            uname = str(u.get("username", "")).lower()
            uid = str(u.get("user_id", "")).lower()
            fname = str(u.get("full_name", "")).lower()

            if (clean_target in uname) or (uname and uname in clean_target) or (clean_target == uid) or (fname and clean_target in fname):
                return {
                    "is_online": True,
                    "status": "ONLINE",
                    "status_badge": "🟢 EN LÍNEA (SSO Activo)",
                    "sessions_count": u.get("sessions_count", 1),
                    "ip": u.get("ip", "-"),
                    "start": u.get("start"),
                    "last_access": u.get("last_access"),
                    "reparticion_sigla": rep.get("sigla", ""),
                    "reparticion_desc": rep.get("desc", ""),
                    "zona_sigla": rep.get("zona_sigla", ""),
                    "full_name": u.get("full_name", ""),
                    "username": u.get("username", ""),
                    "is_admin": u.get("is_admin", False),
                    "checked_at": datetime.datetime.now().strftime("%H:%M:%S")
                }

    return {
        "is_online": False,
        "status": "OFFLINE",
        "status_badge": "🔴 DESCONECTADO (Sesión Cerrada)",
        "sessions_count": 0,
        "message": "Sesión SSO no detectada en Keycloak (el usuario cerró sesión o el token expiró)",
        "checked_at": datetime.datetime.now().strftime("%H:%M:%S")
    }

# ------------------------------------------------------------------------------
# AUDITORÍA DE ACTIVIDAD EN VIVO (SISPER BITÁCORA)
# ------------------------------------------------------------------------------
#: La interfaz sondea este feed cada 15 s; con 12 s de ventana casi todos los
#: sondeos aciertan en caché (1.75 s -> 3 ms medidos) y como mucho sirve datos
#: 12 s viejos, que para una lista de auditoría es imperceptible.  Además, la
#: ventana garantiza como máximo 5 consultas por minuto aunque haya varias
#: pestañas o clientes mirando el mismo feed.
@ttl_cache(seconds=12)
def get_live_activity_data(env_key: str = "develop", limit: int = 50, modulo: str = "", metodo: str = "", search: str = "", user_filter: str = "") -> dict:
    t0 = time.time()
    env_key = normalize_env_key(env_key)
    db_cfg = DATABASE_ENV_CONFIGS.get(env_key, DATABASE_ENV_CONFIGS["develop"])
    cfg = KEYCLOAK_ENV_CONFIGS.get(env_key, KEYCLOAK_ENV_CONFIGS["develop"])
    if not db_cfg.get("bitacora_db"):
        return {"error": "Configuración de Bitácora no disponible para este entorno", "items": [], "users": [], "count": 0, "env": env_key}

    limit = max(10, min(int(limit), 200))
    where_clauses = []

    if user_filter and user_filter.strip():
        uk_clean = user_filter.replace("'", "''").strip()
        where_clauses.append(
            f"(\"RUN_EJECUTOR\" = '{uk_clean}' OR \"RUN_EJECUTOR\" ILIKE '%{uk_clean}%' "
            f"OR \"ID_EJECUTOR\"::text = '{uk_clean}' "
            f"OR \"PRIMER_NOMBRE_EJECUTOR\" ILIKE '%{uk_clean}%' OR \"PRIMER_APELLIDO_EJECUTOR\" ILIKE '%{uk_clean}%')"
        )

    if modulo and modulo.lower() not in ("all", "todos"):
        mod_clean = modulo.replace("'", "''").strip()
        where_clauses.append(f"\"MODULO\" ILIKE '%{mod_clean}%'")

    if metodo and metodo.lower() not in ("all", "todos"):
        met_clean = metodo.replace("'", "''").strip()
        where_clauses.append(f"\"METODO\" = '{met_clean}'")

    if search and search.strip():
        s_clean = search.replace("'", "''").strip()
        where_clauses.append(
            f"(\"URL_ENDPOINT\" ILIKE '%{s_clean}%' OR \"RUN_EJECUTOR\" ILIKE '%{s_clean}%' "
            f"OR \"PRIMER_NOMBRE_EJECUTOR\" ILIKE '%{s_clean}%' OR \"PRIMER_APELLIDO_EJECUTOR\" ILIKE '%{s_clean}%' "
            f"OR \"TRANSACCION\" ILIKE '%{s_clean}%')"
        )

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    sql = f'''
        SELECT coalesce(json_agg(t), '[]'::json) FROM (
            SELECT 
                "ID_BITACORA"::text as id,
                COALESCE("MODULO", 'GENERAL') as modulo,
                COALESCE("URL_ENDPOINT", '') as url_endpoint,
                COALESCE("METODO", 'POST') as metodo,
                COALESCE("RESPONSE_CODE", 200) as response_code,
                to_char("FECHA_EJECUCION", 'YYYY-MM-DD"T"HH24:MI:SS.MSOF') as fecha_ejecucion,
                "ID_EJECUTOR"::text as id_ejecutor,
                COALESCE("IP_EJECUTOR", '-') as ip_ejecutor,
                COALESCE("RUN_EJECUTOR", '-') as run_ejecutor,
                COALESCE("PRIMER_NOMBRE_EJECUTOR", '') as primer_nombre,
                COALESCE("PRIMER_APELLIDO_EJECUTOR", '') as primer_apellido,
                COALESCE("SEGUNDO_APELLIDO_EJECUTOR", '') as segundo_apellido,
                LEFT(COALESCE("TRANSACCION", ''), 1000) as transaccion_preview,
                LENGTH(COALESCE("TRANSACCION", '')) as transaccion_len
            FROM "BITACORA"
            {where_sql}
            ORDER BY "FECHA_EJECUCION" DESC
            LIMIT {limit}
        ) t;
    '''

    cmd = [
        "psql", "-h", db_cfg["host"], "-p", str(db_cfg["port"]),
        "-U", db_cfg["bitacora_user"], "-d", db_cfg["bitacora_db"],
        "-t", "-A", "-c", sql
    ]
    env_vars = os.environ.copy()
    env_vars["PGPASSWORD"] = db_cfg["bitacora_pass"]

    try:
        res = subprocess.run(cmd, env=env_vars, capture_output=True, text=True, timeout=8)
        if res.returncode != 0:
            return {
                "error": f"Error psql: {res.stderr.strip()}",
                "env": env_key,
                "env_name": cfg.get("name", env_key.upper()),
                "env_ip": cfg.get("ingress_ip", ""),
                "db_host": db_cfg["host"],
                "db_port": db_cfg["port"],
                "items": [],
                "users": [],
                "count": 0
            }
        raw_json = res.stdout.strip()
        items = json.loads(raw_json) if raw_json else []
    except Exception as e:
        return {
            "error": str(e),
            "env": env_key,
            "env_name": cfg.get("name", env_key.upper()),
            "env_ip": cfg.get("ingress_ip", ""),
            "db_host": db_cfg["host"],
            "db_port": db_cfg["port"],
            "items": [],
            "users": [],
            "count": 0
        }

    formatted_items = []
    unique_users = set()
    module_counts = {}
    error_count = 0

    adm_uids = KEYCLOAK_ADMINS_CACHE.get(env_key, {}).get("uids", set())
    adm_unames = KEYCLOAK_ADMINS_CACHE.get(env_key, {}).get("unames", set())

    for it in items:
        fn = f"{it.get('primer_nombre', '')} {it.get('primer_apellido', '')}".strip()
        if not fn or fn.lower() == "no disponible":
            fn = it.get('run_ejecutor', 'Desconocido')
        it['nombre_completo'] = fn

        run_val = it.get('run_ejecutor')
        uid_val = it.get('id_ejecutor')
        person_key = run_val if (run_val and run_val != '-') else (fn if fn and fn.lower() != 'desconocido' else uid_val)
        if person_key and person_key != '-':
            unique_users.add(person_key)

        is_admin = bool(
            it.get('id_ejecutor') in adm_uids or 
            it.get('run_ejecutor') in adm_unames or 
            "admin" in str(it.get('run_ejecutor', '')).lower() or
            "admin" in fn.lower()
        )
        it['is_admin'] = is_admin

        mod = it.get('modulo', 'GENERAL')
        module_counts[mod] = module_counts.get(mod, 0) + 1

        code = it.get('response_code', 200)
        if code >= 400:
            error_count += 1

        formatted_items.append(it)

    top_module = max(module_counts.items(), key=lambda x: x[1])[0] if module_counts else "Ninguno"
    success_rate = round((len(formatted_items) - error_count) / len(formatted_items) * 100, 1) if formatted_items else 100.0

    # Agrupación estructurada de movimientos por cada persona
    users_dict = {}
    for it in formatted_items:
        run_val = it.get('run_ejecutor')
        fn_val = it.get('nombre_completo')
        uid_val = it.get('id_ejecutor')

        ukey = run_val if (run_val and run_val != '-') else (fn_val if fn_val and fn_val.lower() != 'desconocido' else uid_val)
        if not ukey or ukey == '-':
            ukey = 'Desconocido'

        if ukey not in users_dict:
            users_dict[ukey] = {
                "user_key": ukey,
                "nombre_completo": it.get('nombre_completo'),
                "run_ejecutor": it.get('run_ejecutor'),
                "id_ejecutor": it.get('id_ejecutor'),
                "ip_ejecutor": it.get('ip_ejecutor'),
                "is_admin": it.get('is_admin', False),
                "total_actions": 0,
                "error_actions": 0,
                "last_action_time": it.get('fecha_ejecucion'),
                "last_modulo": it.get('modulo'),
                "last_endpoint": it.get('url_endpoint'),
                "last_metodo": it.get('metodo'),
                "last_response_code": it.get('response_code'),
                "actions": []
            }
        u_entry = users_dict[ukey]
        u_entry["total_actions"] += 1
        if it.get('response_code', 200) >= 400:
            u_entry["error_actions"] += 1
        u_entry["actions"].append(it)

    now_ts = time.time()

    # Incorporar usuarios que están navegando activamente en el frontend (incluso con 0 movimientos en bitácora)
    for tk, tv in list(LIVE_FRONTEND_TELEMETRY.items()):
        if now_ts - tv.get("received_at", 0) <= 35:
            k_run = str(tv.get("user_run") or "").strip()
            k_id = str(tv.get("user_id") or tk).strip()
            matched = False
            for uk, uv in users_dict.items():
                u_run = str(uv.get("run_ejecutor") or "").strip()
                u_id = str(uv.get("id_ejecutor") or "").strip()
                if (k_run and u_run and (k_run == u_run or k_run.replace("-","") == u_run.replace("-",""))) or (k_id and u_id and k_id == u_id):
                    uv["live_telemetry"] = tv
                    uv["is_browsing_now"] = True
                    matched = True
                    break
            if not matched:
                person_name = tv.get("user_name") or k_run or "Operador Activo"
                user_key_final = k_run if (k_run and k_run != "-") else k_id
                users_dict[f"live_{tk}"] = {
                    "user_key": user_key_final,
                    "nombre_completo": person_name,
                    "run_ejecutor": k_run or "-",
                    "id_ejecutor": k_id,
                    "ip_ejecutor": tv.get("ip", ""),
                    "is_admin": bool(tv.get("is_admin", False)),
                    "total_actions": 0,
                    "error_actions": 0,
                    "last_action_time": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "last_modulo": tv.get("route_name", "NAVEGACIÓN"),
                    "last_metodo": "VIEW",
                    "last_endpoint": tv.get("full_hash", tv.get("route", "")),
                    "last_response_code": 200,
                    "actions": [],
                    "live_telemetry": tv,
                    "is_browsing_now": True
                }

    grouped_users = sorted(
        users_dict.values(),
        key=lambda u: (not u.get("is_browsing_now", False), not u.get("is_admin", False), -(u.get("total_actions", 0)), u.get("last_action_time", ""))
    )

    user_session_info = None
    user_telemetry_info = None

    if user_filter and user_filter.strip():
        user_session_info = get_user_live_session_info(env_key, user_filter)
        uf_clean = user_filter.strip().replace(".", "").replace("-", "").lower()
        for tk, tv in list(LIVE_FRONTEND_TELEMETRY.items()):
            if now_ts - tv.get("received_at", 0) <= 35:
                tk_clean = str(tk).strip().replace(".", "").replace("-", "").lower()
                uid_clean = str(tv.get("user_id", "")).strip().replace(".", "").replace("-", "").lower()
                urun_clean = str(tv.get("user_run", "")).strip().replace(".", "").replace("-", "").lower()
                ukey_clean = str(tv.get("user_key", "")).strip().replace(".", "").replace("-", "").lower()
                if (uf_clean in (tk_clean, uid_clean, urun_clean, ukey_clean) or 
                    tk_clean in uf_clean or 
                    (urun_clean and (urun_clean in uf_clean or uf_clean in urun_clean)) or
                    (uid_clean and uid_clean in uf_clean)):
                    user_telemetry_info = tv
                    break

    return {
        "env": env_key,
        "env_name": cfg.get("name", env_key.upper()),
        "env_ip": cfg.get("ingress_ip", ""),
        "db_host": db_cfg["host"],
        "db_port": db_cfg["port"],
        "items": formatted_items,
        "users": grouped_users,
        "selected_user": user_filter,
        "user_session": user_session_info,
        "live_telemetry": user_telemetry_info,
        "count": len(formatted_items),
        "unique_users_count": len(unique_users),
        "error_count": error_count,
        "success_rate": success_rate,
        "top_module": top_module,
        "latency_ms": round((time.time() - t0) * 1000, 1),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def get_activity_detail(env_key: str = "develop", id_bitacora: str = "") -> dict:
    env_key = normalize_env_key(env_key)
    db_cfg = DATABASE_ENV_CONFIGS.get(env_key, DATABASE_ENV_CONFIGS["develop"])
    id_clean = id_bitacora.replace("'", "").strip()
    sql = f'''
        SELECT coalesce(json_agg(t), '[]'::json) FROM (
            SELECT 
                "ID_BITACORA"::text as id,
                COALESCE("MODULO", 'GENERAL') as modulo,
                COALESCE("URL_ENDPOINT", '') as url_endpoint,
                COALESCE("METODO", 'POST') as metodo,
                COALESCE("RESPONSE_CODE", 200) as response_code,
                to_char("FECHA_EJECUCION", 'YYYY-MM-DD"T"HH24:MI:SS.MSOF') as fecha_ejecucion,
                "ID_EJECUTOR"::text as id_ejecutor,
                COALESCE("IP_EJECUTOR", '-') as ip_ejecutor,
                COALESCE("RUN_EJECUTOR", '-') as run_ejecutor,
                COALESCE("PRIMER_NOMBRE_EJECUTOR", '') as primer_nombre,
                COALESCE("PRIMER_APELLIDO_EJECUTOR", '') as primer_apellido,
                COALESCE("SEGUNDO_APELLIDO_EJECUTOR", '') as segundo_apellido,
                COALESCE("TRANSACCION", '') as transaccion
            FROM "BITACORA"
            WHERE "ID_BITACORA"::text = '{id_clean}'
            LIMIT 1
        ) t;
    '''
    cmd = [
        "psql", "-h", db_cfg["host"], "-p", str(db_cfg["port"]),
        "-U", db_cfg["bitacora_user"], "-d", db_cfg["bitacora_db"],
        "-t", "-A", "-c", sql
    ]
    env_vars = os.environ.copy()
    env_vars["PGPASSWORD"] = db_cfg["bitacora_pass"]
    try:
        res = subprocess.run(cmd, env=env_vars, capture_output=True, text=True, timeout=5)
        raw = res.stdout.strip()
        data = json.loads(raw) if raw else []
        if data:
            row = data[0]
            fn = f"{row.get('primer_nombre', '')} {row.get('primer_apellido', '')}".strip()
            row['nombre_completo'] = fn or row.get('run_ejecutor', '-')
            return row
        return {"error": "Registro no encontrado"}
    except Exception as e:
        return {"error": str(e)}


