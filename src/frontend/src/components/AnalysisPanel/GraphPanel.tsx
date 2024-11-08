import { Stack } from "@fluentui/react";
import { useContext } from "react";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import json from "react-syntax-highlighter/dist/esm/languages/hljs/json";
import { a11yLight } from "react-syntax-highlighter/dist/esm/styles/hljs";
import CytoscapeComponent from 'react-cytoscapejs';

import styles from "./AnalysisPanel.module.css";

import { Thoughts, PAIDRetrievalMode } from "../../api";
import { AppStateContext } from '../../AppStateContext/AppStateContext';

SyntaxHighlighter.registerLanguage("json", json);

interface Props {
    thoughts: Thoughts[];
}

function convertRefs(value: number): number {
    return Math.max(value * 3, 15);
}

export const GraphPanel = ({ thoughts }: Props) => {
    const appStateContext = useContext(AppStateContext);
    if (!appStateContext) {
        throw new Error('Layout component must be used within an AppStateProvider');
    }
    const { sharedState, setSharedState } = appStateContext;

    const decodeSelection = (vector: number, semantic: number, graph: number) => {
        switch (sharedState) {
            case PAIDRetrievalMode.Vector:
                if (vector === 1) return 8;
                break;

            case PAIDRetrievalMode.Semantic:
                if (semantic === 1) return 8;
                break;

            case PAIDRetrievalMode.GraphRAG:
                if (graph === 1) return 8;
                break;
        }
    };
    const decode = (vector: any, semantic: any, graph: any) => {
        switch (sharedState) {
            case PAIDRetrievalMode.Vector:
                return vector;
            case PAIDRetrievalMode.Semantic:
                return semantic;
            case PAIDRetrievalMode.GraphRAG:
                return graph;
        }
    };
    const elements = [
        // GraphRAG
        { data: { id: '615468',  refs: convertRefs(5),  selection: decodeSelection(1,1,1), color: '#ed8035', label: 'Le Vette v. Hardman Estate' }, position: { x: 850, y: 600 } },
        { data: { id: '4975399', refs: convertRefs(12), selection: decodeSelection(0,1,1), color: '', label: 'Laurelon Terrace, Inc. v. City of Seattle' }, position: { x: 1100, y: 320 } }, //selected in semantic
        { data: { id: '1034620', refs: convertRefs(5),  selection: decodeSelection(0,1,1), color: '#ed8035', label: 'Jorgensen v. Massart' }, position: { x: 250, y: 220 } },
        { data: { id: '1127907', refs: convertRefs(22), selection: decodeSelection(0,0,1), color: '#ed8035', label: 'Foisy v. Wyman' }, position: { x: 700, y: 180 } },
        { data: { id: '1095193', refs: convertRefs(7),  selection: decodeSelection(0,1,1), color: '#ed8035', label: 'Thomas v. Housing Authority' }, position: { x: 430, y: 300 } },
        { data: { id: '1186056', refs: convertRefs(40), selection: decodeSelection(0,0,1), color: '#ed8035', label: 'Stuart v. Coldwell Banker Commercial Group, Inc.' }, position: { x: 950, y: 140 } },
        { data: { id: '4953587', refs: convertRefs(13), selection: decodeSelection(0,0,1), color: '', label: 'Schedler v. Wagner' }, position: { x: 800, y: 350 } },
        { data: { id: '2601920', refs: convertRefs(10), selection: decodeSelection(0,0,1), color: '#ed8035', label: 'Pappas v. Zerwoodis' }, position: { x: 500, y: 400 } },
        { data: { id: '594079',  refs: convertRefs(1),  selection: decodeSelection(1,1,1), color: '#ed8035', label: 'Martindale Clothing Co. v. Spokane & Eastern Trust Co.' }, position: { x: 530, y: 590 } },
        { data: { id: '1279441', refs: convertRefs(9),  selection: decodeSelection(0,0,1), color: '', label: 'Tope v. King County' }, position: { x: 950, y: 490 } },

        // GraphRAG Refs
        { data: { id: '615468-1',  refs: 15 }, position: { x: 820, y: 540 } }, // { x: 850, y: 660 } }
        { data: { id: '4975399-1',  refs: 15 }, position: { x: 1070, y: 260 } }, // { x: 1100, y: 320 } }
        { data: { id: '4975399-2',  refs: 15 }, position: { x: 1130, y: 260 } }, // { x: 1100, y: 320 } }
        { data: { id: '1034620-1',  refs: 15 }, position: { x: 280, y: 160 } }, // { x: 250, y: 220 } }
        { data: { id: '1127907-1',  refs: 15 }, position: { x: 670, y: 100 } }, // { x: 700, y: 180 } }
        { data: { id: '1127907-2',  refs: 15 }, position: { x: 730, y: 100 } }, // { x: 700, y: 180 } }
        { data: { id: '1127907-3',  refs: 15 }, position: { x: 630, y: 125 } }, // { x: 700, y: 180 } }
        { data: { id: '1127907-4',  refs: 15 }, position: { x: 770, y: 125 } }, // { x: 700, y: 180 } }
        { data: { id: '1095193-1',  refs: 15 }, position: { x: 460, y: 240 } }, // { x: 430, y: 300 } }
        { data: { id: '1186056-1',  refs: 15 }, position: { x: 930, y: 10 } }, // { x: 950, y: 140 } }
        { data: { id: '1186056-2',  refs: 15 }, position: { x: 970, y: 10 } }, // { x: 950, y: 140 } }
        { data: { id: '1186056-3',  refs: 15 }, position: { x: 900, y: 16 } }, // { x: 950, y: 140 } }
        { data: { id: '1186056-4',  refs: 15 }, position: { x: 1000, y: 16 } }, // { x: 950, y: 140 } }
        { data: { id: '1186056-5',  refs: 15 }, position: { x: 870, y: 30 } }, // { x: 950, y: 140 } }
        { data: { id: '1186056-6',  refs: 15 }, position: { x: 1030, y: 30 } }, // { x: 950, y: 140 } }
        { data: { id: '1186056-7',  refs: 15 }, position: { x: 845, y: 45 } }, // { x: 950, y: 140 } }
        { data: { id: '1186056-8',  refs: 15 }, position: { x: 1055, y: 45 } }, // { x: 950, y: 140 } }
        { data: { id: '4953587-1',  refs: 15 }, position: { x: 770, y: 290 } }, // { x: 800, y: 350 } }
        { data: { id: '4953587-2',  refs: 15 }, position: { x: 830, y: 290 } }, // { x: 800, y: 350 } }
        { data: { id: '2601920-1',  refs: 15 }, position: { x: 470, y: 340 } }, // { x: 500, y: 400 } }
        { data: { id: '2601920-2',  refs: 15 }, position: { x: 530, y: 340 } }, // { x: 500, y: 400 } }
        { data: { id: '594079-1',  refs: 15 }, position: { x: 500, y: 530 } }, // { x: 530, y: 650 } }
        { data: { id: '1279441-1',  refs: 15 }, position: { x: 920, y: 430 } }, // { x: 950, y: 550 } }
        { data: { id: '1279441-2',  refs: 15 }, position: { x: 980, y: 430 } }, // { x: 950, y: 550 } }

        // Edges from Graph Refs
        { data: { source: '615468-1', target: '615468' }, classes: 'directed' },
        { data: { source: '4975399-1', target: '4975399' }, classes: 'directed' },
        { data: { source: '4975399-2', target: '4975399' }, classes: 'directed' },
        { data: { source: '1034620-1', target: '1034620' }, classes: 'directed' },
        { data: { source: '1127907-1', target: '1127907' }, classes: 'directed' },
        { data: { source: '1127907-2', target: '1127907' }, classes: 'directed' },
        { data: { source: '1127907-3', target: '1127907' }, classes: 'directed' },
        { data: { source: '1127907-4', target: '1127907' }, classes: 'directed' },
        { data: { source: '1095193-1', target: '1095193' }, classes: 'directed' },
        { data: { source: '1186056-1', target: '1186056' }, classes: 'directed' },
        { data: { source: '1186056-2', target: '1186056' }, classes: 'directed' },
        { data: { source: '1186056-3', target: '1186056' }, classes: 'directed' },
        { data: { source: '1186056-4', target: '1186056' }, classes: 'directed' },
        { data: { source: '1186056-5', target: '1186056' }, classes: 'directed' },
        { data: { source: '1186056-6', target: '1186056' }, classes: 'directed' },
        { data: { source: '1186056-7', target: '1186056' }, classes: 'directed' },
        { data: { source: '1186056-8', target: '1186056' }, classes: 'directed' },
        { data: { source: '4953587-1', target: '4953587' }, classes: 'directed' },
        { data: { source: '4953587-2', target: '4953587' }, classes: 'directed' },
        { data: { source: '2601920-1', target: '2601920' }, classes: 'directed' },
        { data: { source: '2601920-2', target: '2601920' }, classes: 'directed' },
        { data: { source: '594079-1', target: '594079' }, classes: 'directed' },
        { data: { source: '1279441-1', target: '1279441' }, classes: 'directed' },
        { data: { source: '1279441-2', target: '1279441' }, classes: 'directed' },

        // Semantic
        { data: { id: '481657',   refs: convertRefs(0),  selection: decodeSelection(0,1,0), color: '', label: 'Swanson v. White & Bollard, Inc.' }, position: { x: 270, y: 470 } },
        { data: { id: '630224',   refs: convertRefs(1),  selection: decodeSelection(1,1,0), color: '', label: 'Imperial Candy Co. v. City of Seattle' }, position: { x: 1200, y: 600 } },
        { data: { id: '1346648',  refs: convertRefs(3),  selection: decodeSelection(1,1,0), color: '', label: 'Tombari v. City of Spokane' }, position: { x: 680, y: 495 } },
        { data: { id: '768356',   refs: convertRefs(3),  selection: decodeSelection(1,1,0), color: '#ed8035', label: 'Uhl Bros. v. Hull' }, position: { x: 1080, y: 540 } },
        { data: { id: '1005731',  refs: convertRefs(0),  selection: decodeSelection(0,1,0), color: '#ed8035', label: 'Finley v. City of Puyallup' }, position: { x: 650, y: 300 } },

        // Vector
        { data: { id: '674990',   refs: convertRefs(0),  selection: decodeSelection(1,0,0), color: '', label: 'Woolworth Co. v. City of Seattle' }, position: { x: 220, y: 560 } },
        { data: { id: '4938756',  refs: convertRefs(5),  selection: decodeSelection(1,0,0), color: '', label: 'Stevens v. King County' }, position: { x: 270, y: 340 } },
        { data: { id: '5041745',  refs: convertRefs(0),  selection: decodeSelection(1,0,0), color: '', label: 'Frisken v. Art Strand Floor Coverings, Inc.' }, position: { x: 1250, y: 240 } },
        { data: { id: '1017660',  refs: convertRefs(4),  selection: decodeSelection(1,0,0), color: '#ed8035', label: 'United Mutual Savings Bank v. Riebli' }, position: { x: 1170, y: 200 } },
        { data: { id: '782330',   refs: convertRefs(0),  selection: decodeSelection(1,0,0), color: '', label: 'DeHoney v. Gjarde' }, position: { x: 1230, y: 540 } },

        // Vector Refs
        { data: { id: '4938756-1',  refs: 15 }, position: { x: 300, y: 280 } }, // { x: 270, y: 340 } }
        { data: { id: '1017660-1',  refs: 15 }, position: { x: 1200, y: 140 } }, // { x: 1170, y: 200 } }

        // Edges from Vector Refs
        { data: { source: '4938756-1', target: '4938756' }, classes: 'directed' },
        { data: { source: '1017660-1', target: '1017660' }, classes: 'directed' },

     ];
    return (
        <div style={{ position: 'relative', width: '99%' }}>
            <div style={{ position: 'absolute', top: '10px', left: '10px', zIndex: 1 }} 
                 className={styles.graphRecall}>
                Recall: <span style={{ color: decode('red', '#0fd406', '#0fd406') }}>{decode('40%', '60%', '70%')}</span>
            </div>
            <CytoscapeComponent 
                elements={elements} 
                className={styles.graphContainer} 
                style={{ width: '100%', height: '640px' }}
                layout={{ name: 'preset' }}
                stylesheet={[
                    {
                        selector: 'node',
                        style: {
                            'label': 'data(label)',
                            'width': 'data(refs)',
                            'height': 'data(refs)',
                            'background-color': 'data(color)',
                            'outline-color': '#0fd406',
                            'outline-opacity': 0.7,
                            'outline-width': 'data(selection)',
                            'outline-style': 'solid',
                            'outline-offset': 6,
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'curve-style': 'bezier',
                            'target-arrow-shape': 'triangle',
                            'width': 1,
                        }
                    }
                ]}
            />
        </div>
    );
};
