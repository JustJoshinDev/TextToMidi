from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QFileDialog, QLabel, QHBoxLayout, QLineEdit
from PySide6.QtCore import Qt
from mido import Message, MidiFile, MidiTrack, bpm2tempo
import sys
import re

# Map sharps only; will convert flats to sharps internally
note_map = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4,
            'F': 5, 'F#': 6, 'G': 7, 'G#': 8,
            'A': 9, 'A#': 10, 'B': 11}

def normalize_note_name(note):
    """
    Convert flats (e.g. Bb) to sharps (A#),
    strip chord qualities (like m, maj7),
    and return pitch and octave.
    """
    note = note.strip().upper()
    if note in ['R', 'REST']:
        return 'R', None  # Special case for rest

    # Match pitch+optional accidental + octave at the end
    match = re.match(r"^([A-G])([#B]?)(\d)$", note)
    if not match:
        # Could not parse note properly
        raise ValueError(f"Invalid note format: '{note}'")

    pitch, accidental, octave_str = match.groups()

    # Convert flat to sharp equivalent
    if accidental == 'B':
        # Flats mapping
        flat_to_sharp = {
            'A': 'G#',
            'B': 'A#',
            'C': 'B',
            'D': 'C#',
            'E': 'D#',
            'F': 'E',
            'G': 'F#'
        }
        pitch = flat_to_sharp.get(pitch, pitch)
        accidental = ''  # now handled in pitch (e.g. G#)

    full_pitch = pitch + accidental
    octave = int(octave_str)

    if full_pitch not in note_map:
        raise ValueError(f"Note '{full_pitch}' is not valid after normalization")

    return full_pitch, octave

def note_to_midi(note):
    if note == 'R':
        return None
    pitch, octave = normalize_note_name(note)
    return 12 + note_map[pitch] + 12 * octave

def parse_text_to_midi(text, bpm=90):
    midi = MidiFile()
    track = MidiTrack()
    midi.tracks.append(track)
    tempo = bpm2tempo(bpm)

    track.append(Message('program_change', program=0, time=0))
    ticks_per_beat = midi.ticks_per_beat

    for line in text.strip().splitlines():
        if not line.strip():
            continue
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        notes_part = parts[0]
        try:
            duration = float(parts[1])
        except ValueError:
            continue  # skip lines with bad duration
        velocity = int(parts[2]) if len(parts) > 2 else 64

        notes = [n.strip() for n in notes_part.split(',')]

        # Calculate ticks for duration
        duration_ticks = int(ticks_per_beat * duration)

        # Note on messages at time=0 (simultaneous notes)
        midi_notes = []
        for n in notes:
            try:
                midi_note = note_to_midi(n)
            except ValueError:
                midi_note = None
            if midi_note is not None:
                midi_notes.append(midi_note)

        if not midi_notes:
            # Rest: add delay only
            track.append(Message('note_off', note=0, velocity=0, time=duration_ticks))
        else:
            for i, midi_note in enumerate(midi_notes):
                track.append(Message('note_on', note=midi_note, velocity=velocity, time=0))

            for i, midi_note in enumerate(midi_notes):
                off_time = duration_ticks if i == 0 else 0
                track.append(Message('note_off', note=midi_note, velocity=velocity, time=off_time))

    return midi

class MidiMaker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Text to MIDI Converter")
        self.setGeometry(200, 200, 600, 500)

        layout = QVBoxLayout()

        label = QLabel("Enter notes and durations (e.g. C4 1.0 or C4,E4,G4 2.0). Velocity optional (e.g. A4 1.0 90). Use R or Rest for rests.")
        layout.addWidget(label)

        bpm_layout = QHBoxLayout()
        bpm_label = QLabel("Tempo (BPM):")
        self.bpm_input = QLineEdit("90")
        self.bpm_input.setMaximumWidth(60)
        bpm_layout.addWidget(bpm_label)
        bpm_layout.addWidget(self.bpm_input)
        bpm_layout.addStretch()
        layout.addLayout(bpm_layout)

        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)

        self.button = QPushButton("Export MIDI")
        self.button.clicked.connect(self.export_midi)
        layout.addWidget(self.button)

        self.setLayout(layout)

    def export_midi(self):
        text = self.text_edit.toPlainText()
        try:
            bpm = int(self.bpm_input.text())
        except:
            bpm = 90
        try:
            midi = parse_text_to_midi(text, bpm)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error", f"Failed to parse input:\n{e}")
            return
        filename, _ = QFileDialog.getSaveFileName(self, "Save MIDI File", "output.mid", "MIDI Files (*.mid)")
        if filename:
            midi.save(filename)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MidiMaker()
    window.show()
    sys.exit(app.exec())
