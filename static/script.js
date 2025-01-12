const socket = io();
const gallery = document.querySelector('#gallery');

function fetchAllImages() {
    fetch('/get-images')
        .then(response => response.json())
        .then(images => {
            // Display all images initially
            images.forEach(image => {
                const img = document.createElement('img');
                img.src = `/static/uploads/${image}`;
                img.alt = image;
                img.classList.add('image-gallery-img');

                gallery.appendChild(img);
            });
        })
        .catch(err => console.error('Error fetching images:', err));
}

// Call the function to load all images on page load
fetchAllImages();

// When a new image is received via socket.io
socket.on('new_image', (data) => {
    const img = document.createElement('img');
    img.src = `/static/uploads/${data.filename}`;
    img.alt = data.filename;
    img.classList.add('image-gallery-img');

    gallery.prepend(img);
});
