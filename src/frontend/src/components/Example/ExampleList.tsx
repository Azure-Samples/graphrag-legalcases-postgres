import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "Water leaking into the apartment from the floor above. What are the prominent legal precedents in Washington on this problem?",
    "When the landlord is sued in court for leaking pipes, how many times did it result in a favorable decision for the renter?",
];

interface Props {
    onExampleClicked: (value: string) => void
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {DEFAULT_EXAMPLES.map((question, i) => (
                <li key={i}>
                    <Example text={question} value={question} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
