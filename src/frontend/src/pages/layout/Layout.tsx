import { Outlet, Link } from "react-router-dom";
import { SetStateAction, useState } from "react";
import styles from "./Layout.module.css";
import { PAIDRetrievalMode } from "../../api";
import React, { useContext } from 'react';
import { AppStateContext } from '../../AppStateContext/AppStateContext';

interface RetrievalModeProps {
    updatePAIDRetrievalMode: (retrievalMode: PAIDRetrievalMode) => void;
}

const Layout = () => {
    const [selectedMode, setSelectedMode] = useState("Vector Search");
    const appStateContext = useContext(AppStateContext);
    if (!appStateContext) {
        throw new Error('Layout component must be used within an AppStateProvider');
    }
    const { sharedState, setSharedState } = appStateContext;

    const handleModeChange = (event: { target: { value: SetStateAction<string>; }; }) => {
        setSelectedMode(event.target.value);
        console.log("handleModeChange: " + (event.target.value as PAIDRetrievalMode).toString());
        setSharedState((prev: any) => (event.target.value as PAIDRetrievalMode));
    };

    return (
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"}>
                <div className={styles.headerContainer}>
                    <Link to="/" className={styles.headerTitleContainer}>
                        <h3 className={styles.headerTitle}>Legal Research Assistant</h3>
                    </Link>

                    <div className={styles.radioContainer}>
                        <label>
                            <input
                                type="radio"
                                value="Vector Search"
                                checked={selectedMode === "Vector Search"}
                                onChange={handleModeChange}
                                className={styles.radioInput}
                            />
                            Vector Search
                        </label>
                        <label>
                            <input
                                type="radio"
                                value="Semantic Ranker"
                                checked={selectedMode === "Semantic Ranker"}
                                onChange={handleModeChange}
                                className={styles.radioInput}
                            />
                            Semantic Ranker
                        </label>
                        <label>
                            <input
                                type="radio"
                                value="GraphRAG"
                                checked={selectedMode === "GraphRAG"}
                                onChange={handleModeChange}
                                className={styles.radioInput}
                            />
                            GraphRAG
                        </label>
                    </div>

                    <h4 className={styles.headerRightText}>PAID - Postgres AI Demo</h4>
                </div>
            </header>

            <Outlet />
        </div>
    );
};

export default Layout;