
document.addEventListener("click", async (e) => {
    if (!e.target.classList.contains("delete-job-btn")) return;

    const jobId = e.target.dataset.jobId;

    if (!confirm("Are you sure you want to delete this job?")) return;

    try {
        const res = await fetch(`/clipper-delete/${jobId}`, { method: "POST" });

        if (!res.ok) {
            alert("Failed to delete job");
            return;
        }

        e.target.closest(".bg-white").remove();
    } catch (err) {
        console.error(err);
        alert("Error deleting job");
    }
});


document.addEventListener("click", function(e) {

    const img = e.target.closest(".video-thumb");
    if (!img) return;

    const videoSrc = img.dataset.videoSrc;

    const video = document.createElement("video");
    video.controls = true;
    video.preload = "none";
    video.autoplay = true;
    video.className = "w-full h-full object-contain";

    const source = document.createElement("source");
    source.src = videoSrc;

    video.appendChild(source);

    img.parentElement.replaceChild(video, img);
});


