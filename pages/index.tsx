import React, { useState } from "react";
import axios from 'axios';
import styles from '../styles/Home.module.css';

export default function Home() {
  const [typeformOutput, setTypeformOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState(null);

  const handleSubmit = async () => {
    setLoading(true);

    try {
      const response = await axios.post("/api/process-typeform", { data: typeformOutput });

      setLoading(false);
      setOutput(response.data.user_plan);
    } catch (error) {
      console.error("Error:", error);
      setLoading(false);
      alert("An error occurred while processing the Typeform data.");
    }
  };

  return (
    <div className={styles.container}>
      <h1>Mosaic Plan Creator</h1>
      <input
        type="text"
        value={typeformOutput}
        onChange={e => setTypeformOutput(e.target.value)}
        placeholder="Paste the Typeform response here..."
      />
      <button onClick={handleSubmit}>Submit</button>
      {loading && <div>Processing...</div>}
      {output && (
        <div className={styles.outputContainer}>
          <pre>{output}</pre>
        </div>
      )}
    </div>
  );
}