document.getElementById('urlForm').addEventListener('submit', function(e) {
    e.preventDefault();
    console.log("Form submitted");
    
    const url = document.getElementById('chatUrl').value;
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const blogContent = document.getElementById('blogContent');
    const markdownContent = document.getElementById('markdownContent');
    const copyButton = document.getElementById('copyButton');

    // Reset UI elements
    progressBar.style.width = '0%';
    progressText.textContent = 'Initializing...';
    blogContent.style.display = 'none';
    markdownContent.innerHTML = '';
    copyButton.style.display = 'none';
    document.getElementById('progressContainer').style.display = 'block';

    let accumulatedContent = '';
    let typingQueue = [];
    let isTyping = false;
    let totalChunks = 0;
    let processedChunks = 0;

    fetch('/generate-blog', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url })
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        function read() {
            return reader.read().then(({ done, value }) => {
                if (done) {
                    console.log('Stream complete');
                    processAccumulatedContent(true);
                    return;
                }
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));
                        console.log("Received update:", data);

                        if (data.chunk) {
                            accumulatedContent += data.chunk;
                            processAccumulatedContent();
                        }

                        if (data.progress !== undefined) {
                            updateProgress(data.progress);
                        }

                        if (data.progress === 100) {
                            if (!data.chunk) {
                                console.error("Error generating blog:", data.status);
                            }
                            copyButton.style.display = 'block';
                        }
                    }
                });

                return read();
            });
        }

        function processAccumulatedContent(isComplete = false) {
            const contentToProcess = isComplete ? accumulatedContent : accumulatedContent.split('\n').slice(0, -1).join('\n');
            if (contentToProcess) {
                const lines = contentToProcess.split('\n');
                let combinedLine = '';
                lines.forEach(line => {
                    if (line.trim().startsWith('#')) {
                        // Flush the combinedLine buffer
                        if (combinedLine.trim()) {
                            parseInlineMarkdown(combinedLine).forEach(item => typingQueue.push(item));
                            typingQueue.push({ type: 'newline' });
                            combinedLine = '';
                        }
                        // Ensure newline before heading
                        if (typingQueue.length > 0 && typingQueue[typingQueue.length - 1].type !== 'newline') {
                            typingQueue.push({ type: 'newline' });
                        }
                        // Process heading
                        typingQueue.push({ type: 'heading', content: line.trim() });
                        typingQueue.push({ type: 'newline' });
                    } else {
                        // Append line to combinedLine buffer
                        combinedLine += (combinedLine ? ' ' : '') + line;
                    }
                });
                // Flush any remaining combinedLine buffer
                if (combinedLine.trim()) {
                    parseInlineMarkdown(combinedLine).forEach(item => typingQueue.push(item));
                    typingQueue.push({ type: 'newline' });
                }
                processedChunks++;
                if (!isTyping) {
                    typeNextItem();
                }
            }
            accumulatedContent = isComplete ? '' : accumulatedContent.split('\n').slice(-1)[0];
        }

        function parseInlineMarkdown(text) {
            const parts = [];
            let currentText = '';
            let isBold = false;

            for (let i = 0; i < text.length; i++) {
                if (text[i] === '*' && text[i+1] === '*') {
                    if (currentText) {
                        parts.push({ type: 'text', content: currentText, bold: isBold });
                        currentText = '';
                    }
                    isBold = !isBold;
                    i++; // Skip next asterisk
                } else {
                    currentText += text[i];
                }
            }

            if (currentText) {
                parts.push({ type: 'text', content: currentText, bold: isBold });
            }

            return parts;
        }

        function typeNextItem() {
            if (typingQueue.length === 0) {
                isTyping = false;
                return;
            }
            isTyping = true;

            const item = typingQueue.shift();
            if (item.type === 'text') {
                let lastParagraph = markdownContent.lastElementChild;
                if (!lastParagraph || lastParagraph.tagName !== 'P') {
                    lastParagraph = document.createElement('p');
                    markdownContent.appendChild(lastParagraph);
                }
                const span = document.createElement('span');
                span.textContent = item.content;
                if (item.bold) span.style.fontWeight = 'bold';
                lastParagraph.appendChild(span);
            } else if (item.type === 'heading') {
                const level = (item.content.match(/^#+/) || [''])[0].length;
                const heading = document.createElement(`h${level}`);
                heading.textContent = item.content.replace(/^#+\s*/, '');
                markdownContent.appendChild(heading);
            } else if (item.type === 'newline') {
                const lastElement = markdownContent.lastElementChild;
                if (lastElement && lastElement.tagName === 'P' && lastElement.textContent.trim() !== '') {
                    markdownContent.appendChild(document.createElement('p'));
                }
            }

            blogContent.style.display = 'block';
            markdownContent.scrollTop = markdownContent.scrollHeight;

            // Schedule the next item typing immediately
            requestAnimationFrame(typeNextItem);
        }

        function updateProgress(progress) {
            progressBar.style.width = `${progress}%`;
            progressText.textContent = `Generating... ${Math.round(progress)}%`;
        }

        return read();
    }).catch(error => {
        console.error("Fetch failed:", error);
        progressText.textContent = "An error occurred while generating the blog.";
        progressBar.style.width = '100%';
    });
});

document.getElementById('copyButton').addEventListener('click', function() {
    const blogContent = document.getElementById('markdownContent').textContent;
    navigator.clipboard.writeText(blogContent).then(function() {
        alert('Blog content copied to clipboard!');
    }, function(err) {
        console.error('Could not copy text: ', err);
    });
});
