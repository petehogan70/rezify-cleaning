import { useState, useEffect, useRef } from "react";
import { BrowserRouter } from "react-router-dom";


function IndexAIDemo() {
    const demoSteps = [
        { text: "> Initializing Rezify AI Core...", cls: "cmd", i: 0 },
        { text: "Accessing resume data...", cls: "out", i: 0 },
        { text: "Applying NLP models...", cls: "out", i: 0 },
        { text: "Cross-referencing skills matrix...", cls: "out", i: 0},
        { text: "Identifying top internship matches...", cls: "out", i: 0 },
        { text: "✔ Analysis Complete. Results ready.", cls: "ok", i: 0}
    ];
    
    const [lines, setLines] = useState([]);
    const [barWidth, setBarWidth] = useState("0%");
    const containerRef = useRef(null);

    const currLines = useRef(lines);

    useEffect(() => {
        currLines.current = lines;
        }, [lines]);
    
    function typeLine(step, callback) {
        setLines(prevLines => [...prevLines, step]);
        let i = 0;
        const typingInterval = setInterval(() => {
            setLines(prevLines => {
                const updatedLines = [...prevLines];
                const last = { ...updatedLines[updatedLines.length - 1], i: i };
                updatedLines[updatedLines.length - 1] = last;
                return updatedLines;
              });
            i++;
            if (i >= step.text.length) {
                clearInterval(typingInterval);
                if (callback) callback();
            }
        }, 50); // Adjust typing speed (milliseconds per character)
    }
      
    async function runFullDemo() {

        while (true) {
            setLines([])
            setBarWidth("0%");
        
            for (let i = 0; i < demoSteps.length; i++) {
                await new Promise(resolve => typeLine(demoSteps[i], resolve));
                setBarWidth(((i + 1) / demoSteps.length) * 100 + "%");
                // Pause between lines
                if (i < demoSteps.length - 1) {
                    await new Promise(r => setTimeout(r, 300));
                    if (containerRef.current) {
                        containerRef.current.scrollTop = containerRef.current.scrollHeight;
                    }
                }
            }
            // Pause before restarting the demo
            await new Promise(r => setTimeout(r, 3000));
        }
    }
    useEffect(() => {
        runFullDemo();
    }, []);

    return(<div class="ai-demo-output">
        <div id="demo-text-container" ref={containerRef}>
            {lines.map((thing => {
                return  <div className={thing.cls}>{thing.text.substring(0, thing.i)}</div>
            }))}
            <div><br></br></div>
            <div><br></br></div>
        </div>
        <div class="demo-progress-bar-container">
          <div class="demo-progress-bar-fill" style={{width: barWidth}}></div>
        </div>
        <p class="ai-tagline">Rezify AI: Optimizing your internship hunt.</p>
      </div>);
}

export {IndexAIDemo}