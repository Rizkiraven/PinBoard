// Fungsi untuk toggle like
async function toggleLike(postId) {
    try {
        const response = await fetch(`/like/${postId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error processing like');
        }
        
        // Dapatkan elemen yang perlu diupdate
        const postElement = document.querySelector(`.pin-item[data-post-id="${postId}"]`);
        const likeButton = postElement.querySelector('.like-button');
        const likeIcon = likeButton.querySelector('i');
        const likeCount = postElement.querySelector('.like-count');
        
        // Update tampilan like button
        if (data.action === 'liked') {
            likeIcon.classList.remove('far');
            likeIcon.classList.add('fas');
            likeButton.classList.add('text-red-500');
            
            // Tambahkan timestamp like
            const timestampDiv = document.createElement('div');
            timestampDiv.className = 'mt-2 text-xs text-gray-500';
            timestampDiv.textContent = `You liked this post on ${data.liked_at}`;
            
            // Cek apakah sudah ada timestamp, jika ada, update saja
            const existingTimestamp = postElement.querySelector('.text-xs.text-gray-500');
            if (existingTimestamp) {
                existingTimestamp.replaceWith(timestampDiv);
            } else {
                postElement.querySelector('.p-3').appendChild(timestampDiv);
            }
        } else {
            likeIcon.classList.remove('fas');
            likeIcon.classList.add('far');
            likeButton.classList.remove('text-red-500');
            
            // Hapus timestamp like jika ada
            const timestamp = postElement.querySelector('.text-xs.text-gray-500');
            if (timestamp) {
                timestamp.remove();
            }
        }
        
        // Update jumlah like
        likeCount.textContent = `${data.likes_count} likes`;
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error processing like. Please try again.');
    }
}

// Fungsi untuk menampilkan detail like
async function showLikeDetails(postId) {
    try {
        const response = await fetch(`/post/${postId}/likes`);
        const likes = await response.json();
        
        const modal = document.getElementById('likesModal');
        const likesList = document.getElementById('likesList');
        
        // Bersihkan list yang ada
        likesList.innerHTML = '';
        
        // Tambahkan setiap like ke dalam list
        likes.forEach(like => {
            const likeElement = document.createElement('div');
            likeElement.className = 'flex justify-between items-center p-2 hover:bg-gray-100 rounded';
            likeElement.innerHTML = `
                <span class="font-medium">@${like.user_id}</span>
                <span class="text-sm text-gray-500">${like.liked_at}</span>
            `;
            likesList.appendChild(likeElement);
        });
        
        // Tampilkan modal
        modal.classList.add('active');
    } catch (error) {
        console.error('Error:', error);
        alert('Error fetching likes. Please try again.');
    }
}

// Fungsi untuk menutup modal likes
function closeLikesModal() {
    const modal = document.getElementById('likesModal');
    modal.classList.remove('active');
}

// Fungsi untuk pencarian
function openSearch() {
    document.getElementById('searchModal').classList.add('active');
}

function closeSearch() {
    document.getElementById('searchModal').classList.remove('active');
}

// Filter berdasarkan kategori
async function filterByCategory(categoryId) {
    try {
        const response = await fetch(`/search?category=${categoryId}`);
        const data = await response.json();
        
        const searchResults = document.getElementById('searchResults');
        searchResults.innerHTML = '';
        
        data.posts.forEach(post => {
            const postElement = document.createElement('div');
            postElement.className = 'bg-white rounded-lg shadow overflow-hidden';
            postElement.innerHTML = `
                <img src="${post.image_url}" class="w-full h-48 object-cover" alt="${post.title}">
                <div class="p-3">
                    <p class="text-sm">${post.description}</p>
                    <p class="text-xs text-gray-500 mt-2">By @${post.user_id}</p>
                </div>
            `;
            searchResults.appendChild(postElement);
        });
    } catch (error) {
        console.error('Error:', error);
        alert('Error filtering posts. Please try again.');
    }
}

// Event listener saat dokumen dimuat
document.addEventListener('DOMContentLoaded', function() {
    // Tambahkan event listener untuk notifikasi
    const notifications = document.querySelectorAll('.notification');
    notifications.forEach(notification => {
        setTimeout(() => {
            notification.style.display = 'none';
        }, 3000);
    });
});