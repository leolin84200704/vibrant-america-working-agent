import os, sys, paramiko, datetime
host, port, user = "34.199.194.51", 2210, "vibrantamerica"
pw = os.environ["CERBO_PW"]
folders = sys.argv[1:]
t = paramiko.Transport((host, port))
t.connect(username=user, password=pw)
s = paramiko.SFTPClient.from_transport(t)
for f in folders:
    print(f"=== {f} ===")
    try:
        rows = s.listdir_attr(f)
    except Exception as e:
        print("  ERR", e); continue
    rows.sort(key=lambda r: r.st_mtime)
    for r in rows:
        ts = datetime.datetime.utcfromtimestamp(r.st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {ts}Z {r.st_size:>10}  {r.filename}")
    print(f"  ({len(rows)} entries)")
s.close(); t.close()
