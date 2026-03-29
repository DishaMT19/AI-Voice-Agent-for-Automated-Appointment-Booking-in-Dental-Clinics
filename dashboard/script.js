const API = "http://127.0.0.1:8000";

async function loadDashboard() {
  try {
    // ✅ FIX: Add cache-busting query parameter
    const timestamp = new Date().getTime();
    
    let analytics = await fetch(API + "/analytics?t=" + timestamp, {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache'
      }
    }).then(r => r.json());
    document.getElementById("totalAppointments").innerText = analytics.total_appointments;
    document.getElementById("revenue").innerText = "₹ " + analytics.estimated_revenue;

    // ✅ FIX: Cache-bust and backend now returns sorted data
    let appointments = await fetch(API + "/appointments?t=" + timestamp, {
      method: 'GET',
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    }).then(r => r.json());
    
    const tbody = document.querySelector("#apptTable tbody");
    tbody.innerHTML = "";
    
    // ✅ FIX: Backend returns sorted list, show last 50 (most recent first)
    const recentAppointments = Array.isArray(appointments) ? appointments.slice(0, 50) : [];
    
    recentAppointments.forEach(a => {
      let row = document.createElement("tr");
      const confirmId = a.confirmation_id || a.appointment_id || 'N/A';
      const patientName = a.patient?.name || '';
      const service = a.appointment?.service || '';
      const apptDate = a.appointment?.date || '';
      const apptTime = a.appointment?.time || '';
      
      row.innerHTML =
        "<td>" + confirmId + "</td>" +
        "<td>" + patientName + "</td>" +
        "<td>" + service + "</td>" +
        "<td>" + apptDate + "</td>" +
        "<td>" + apptTime + "</td>";
      tbody.appendChild(row);
    });

    new Chart(document.getElementById("serviceChart"), {
      type:"bar",
      data:{labels:Object.keys(analytics.service_counts),
      datasets:[{label:"Count", data:Object.values(analytics.service_counts)}]}
    });

    new Chart(document.getElementById("cityChart"), {
      type:"bar",
      data:{labels:Object.keys(analytics.city_counts),
      datasets:[{label:"Count", data:Object.values(analytics.city_counts)}]}
    });

    new Chart(document.getElementById("emotionChart"), {
      type:"bar",
      data:{labels:Object.keys(analytics.emotion_counts),
      datasets:[{label:"Count", data:Object.values(analytics.emotion_counts)}]}
    });
  } catch (error) {
    console.error('Error loading dashboard:', error);
    document.getElementById('totalAppointments').innerText = 'Error';
  }
}

// ✅ FIX: Initial load + Auto-refresh every 10 seconds
loadDashboard();

// Auto-refresh dashboard every 10 seconds
setInterval(() => {
  console.log('🔄 Auto-refreshing dashboard...');
  loadDashboard();
}, 10000);

document.getElementById("searchBox").addEventListener("keyup", function(){
  let val = this.value.toLowerCase();
  document.querySelectorAll("#apptTable tbody tr").forEach(r=>{
    r.style.display = r.innerText.toLowerCase().includes(val) ? "" : "none";
  });
});

function exportTable(){
  let rows = document.querySelectorAll("table tr");
  let csv = [];
  rows.forEach(r=>{
    let cols = r.querySelectorAll("td,th");
    let line = [];
    cols.forEach(c=>line.push(c.innerText));
    csv.push(line.join(","));
  });
  let blob = new Blob([csv.join("\n")], {type:"text/csv"});
  let url = URL.createObjectURL(blob);
  let a = document.createElement("a");
  a.href=url; a.download="appointments_export.csv"; a.click();
}
