function escapeHtml(s){
  if(s === null || s === undefined) return "";
  return String(s)
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

let busyCount = 0;
function setBusy(on){
  busyCount += (on ? 1 : -1);
  busyCount = Math.max(0, busyCount);
  document.body.style.cursor = busyCount > 0 ? "progress" : "default";
}

function toast(msg){
  const el = document.getElementById("appToast");
  const body = document.getElementById("toastBody");
  if(!el || !body){ return; }
  body.textContent = msg;
  const t = bootstrap.Toast.getOrCreateInstance(el, {delay: 2200});
  t.show();
}
