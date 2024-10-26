document.addEventListener('DOMContentLoaded', () => {
    const notesContainer = document.getElementById('notes-container');
    const addNoteBtn = document.getElementById('add-note-btn');

    let noteId = 0;

    function createNote(title = 'Add Title', content = '.....') {
        const note = document.createElement('div');
        note.className = 'sticky-note';
        note.innerHTML = `
            <input type="text" class="note-title" placeholder="Title" value="${title}">
            <div contenteditable="true" class="note-content">${content}</div>
            <div class="icons-toolbar">
                <button class="icon-btn bold-btn" aria-label="Bold" title="Bold">
                    <i class="uil uil-bold"></i>
                </button>
                <button class="icon-btn italic-btn" aria-label="Italic" title="Italic">
                    <i class="uil uil-italic"></i>
                </button>
                <button class="icon-btn underline-btn" aria-label="Underline" title="Underline">
                    <i class="uil uil-underline"></i>
                </button>
                <button class="icon-btn align-left-btn" aria-label="Align Left" title="Align Left">
                    <i class="uil uil-align-left"></i>
                </button>
                <button class="icon-btn align-center-btn" aria-label="Align Center" title="Align Center">
                    <i class="uil uil-align-center"></i>
                </button>
                <button class="icon-btn align-right-btn" aria-label="Align Right" title="Align Right">
                    <i class="uil uil-align-right"></i>
                </button>
                <input type="color" class="color-picker" aria-label="Color Picker" title="Color Picker">
            </div>
            <button class="delete-btn" aria-label="Delete note" title="Delete note">×</button>
        `;
        note.dataset.id = noteId++;
        notesContainer.appendChild(note);

        const noteContent = note.querySelector('.note-content');

        // Delete button functionality
        const deleteBtn = note.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', () => {
            note.style.transform = 'scale(0)';
            note.addEventListener('transitionend', () => note.remove());
        });

        // Text formatting functionality
        note.querySelector('.bold-btn').addEventListener('click', () => document.execCommand('bold'));
        note.querySelector('.italic-btn').addEventListener('click', () => document.execCommand('italic'));
        note.querySelector('.underline-btn').addEventListener('click', () => document.execCommand('underline'));
        note.querySelector('.align-left-btn').addEventListener('click', () => document.execCommand('justifyLeft'));
        note.querySelector('.align-center-btn').addEventListener('click', () => document.execCommand('justifyCenter'));
        note.querySelector('.align-right-btn').addEventListener('click', () => document.execCommand('justifyRight'));

        // Color picker functionality
        const colorPicker = note.querySelector('.color-picker');
        colorPicker.addEventListener('input', () => {
            noteContent.style.color = colorPicker.value;
        });

        // Focus the content when editing
        noteContent.addEventListener('focus', () => {
            document.execCommand('styleWithCSS', false, true);
        });
    }

    addNoteBtn.addEventListener('click', () => {
        createNote();
    });

    // Initial example note
    createNote();
});
