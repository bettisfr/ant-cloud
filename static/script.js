const socket = io();  // Connect to the WebSocket server
const gallery = document.querySelector('#gallery');  // Select gallery container

// Fetch and display all images from the server
function loadGalleryImages() {
    const filterInput = document.getElementById('filterInput');
    const onlyLabeledCheckbox = document.getElementById('onlyLabeledCheckbox');

    let url = '/get-images';
    const params = [];

    if (filterInput && filterInput.value.trim() !== '') {
        params.push('filter=' + encodeURIComponent(filterInput.value.trim()));
    }

    if (onlyLabeledCheckbox && onlyLabeledCheckbox.checked) {
        params.push('only_labeled=1');  // means NON-labeled only
    }

    if (params.length > 0) {
        url += '?' + params.join('&');
    }

    fetch(url)
        .then(response => response.json())
        .then(images => {
            console.log("Fetched images:", images);

            // server already sorts by timestamp; keep your filename sort if you like
            images.sort((a, b) => b.filename.localeCompare(a.filename));

            gallery.innerHTML = ""; // Clear gallery

            images.forEach(imageData => {
                addImageToGallery(imageData, false); // Add image without real-time effect
            });
        })
        .catch(error => console.error('Error fetching images:', error));
}



// Add an image to the gallery with optional real-time effect
function addImageToGallery(imageData, isRealTime = true) {
    console.log("Adding image:", imageData.filename); // Debugging

    const div = document.createElement('div');
    div.classList.add('col', 'gallery-item');   // add gallery-item for CSS positioning

    // ---- delete button (top-right X) ----
    const deleteBtn = document.createElement('button');
    deleteBtn.classList.add('img-delete-btn');
    deleteBtn.textContent = '×';

    // do NOT open labeler when clicking X
    deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();   // prevent click from bubbling to div
        const ok = confirm(`Delete image "${imageData.filename}" and its labels?`);
        if (!ok) return;

        fetch('/delete-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: imageData.filename })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success' || data.status === 'partial') {
                // remove from DOM
                div.remove();
            } else {
                alert('Delete failed: ' + (data.message || 'unknown error'));
            }
        })
        .catch(err => {
            console.error('Delete error:', err);
            alert('Delete failed: ' + err);
        });
    });

    // Image element with lazy loading
    const img = document.createElement('img');
    img.classList.add('image-gallery-img');
    img.dataset.src = `/static/uploads/${imageData.filename}`;
    img.alt = imageData.filename;
    img.style.visibility = 'hidden';

    // When clicking the image (or the whole div), open labeler
    const host = window.location.hostname;
    const labelerUrl = `http://${host}:5001/label?image=${encodeURIComponent(imageData.filename)}`;

    div.style.cursor = 'pointer';
    div.addEventListener('click', () => {
        window.open(labelerUrl, '_blank');
    });

    const metadataDiv = document.createElement('div');
    metadataDiv.classList.add('image-metadata');
    // metadataDiv.innerHTML = `
    //     <strong>${imageData.filename}</strong><br>
    //     <strong>Labels: ${imageData.labels_count ?? 0}</strong><br>
    //     Temperature: ${imageData.metadata?.temperature ?? 'N/A'} °C<br>
    //     Pressure: ${imageData.metadata?.pressure ?? 'N/A'} hPa<br>
    //     Humidity: ${imageData.metadata?.humidity ?? 'N/A'} %<br>
    //     GPS: (${imageData.metadata?.latitude ?? 'N/A'}, ${imageData.metadata?.longitude ?? 'N/A'})<br>
    //     ${isRealTime ? '<em>Uploaded just now</em>' : ''}
    // `;
    const labeledText = imageData.is_labeled
    ? '🟩 labeled'
    : '⬜ non-labeled';


    metadataDiv.innerHTML = `
        ${imageData.filename}
        (<strong>Labels: ${imageData.labels_count ?? 0}</strong>)<br>
        ${labeledText}
    `;


    // order: X button on top, then img, then metadata
    div.appendChild(deleteBtn);
    div.appendChild(img);
    div.appendChild(metadataDiv);

    if (isRealTime) {
        gallery.prepend(div);
    } else {
        gallery.appendChild(div);
    }

    lazyLoadImage(img);
}

document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('downloadDatasetBtn');
    if (btn) {
        btn.addEventListener('click', () => {
            window.location.href = '/download-dataset';
        });
    }

    const filterInput = document.getElementById('filterInput');
    const onlyLabeledCheckbox = document.getElementById('onlyLabeledCheckbox');

    if (filterInput) {
        // reload on typing (you can debounce later if needed)
        filterInput.addEventListener('input', () => {
            loadGalleryImages();
        });
    }

    if (onlyLabeledCheckbox) {
        onlyLabeledCheckbox.addEventListener('change', () => {
            loadGalleryImages();
        });
    }
});


// Lazy loading for images (loads only when they are near the viewport)
function lazyLoadImage(img) {
    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.src = entry.target.dataset.src;  // Load image
                entry.target.onload = () => entry.target.style.visibility = 'visible'; // Show after loading
                observer.unobserve(entry.target); // Stop observing after loading
            }
        });
    }, { rootMargin: '100px' }); // Load images slightly before they appear on screen

    observer.observe(img);
}

// Listen for real-time image uploads via WebSockets
socket.on('new_image', (data) => {
    addImageToGallery(data, true); // Add new image to gallery
});

// Load all images when the page loads
loadGalleryImages();
