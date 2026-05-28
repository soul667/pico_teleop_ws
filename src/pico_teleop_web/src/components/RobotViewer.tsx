import { OrbitControls, Grid } from '@react-three/drei';

export function RobotViewer() {
  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[5, 5, 5]} intensity={1} />
      <Grid
        args={[10, 10]}
        cellSize={0.1}
        cellThickness={0.5}
        cellColor="#6f6f6f"
        sectionSize={1}
        sectionThickness={1}
        sectionColor="#9d4b4b"
        fadeDistance={10}
        infiniteGrid
      />
      <OrbitControls />
      {/* URDF robot model will be loaded here based on arm config */}
      <mesh position={[0, 0.5, 0]}>
        <boxGeometry args={[0.1, 1, 0.1]} />
        <meshStandardMaterial color="#4a9eff" />
      </mesh>
    </>
  );
}
