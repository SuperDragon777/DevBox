package main

// go build -o hashcalc.exe ~\DevBox\hashcalc\main.go
// Usage: hashcalc -file <filepath> [-algo algorithms] [-verify algo:hash] [-v] [-o output]

import (
	"crypto/md5"
	"crypto/sha1"
	"crypto/sha256"
	"crypto/sha512"
	"encoding/hex"
	"flag"
	"fmt"
	"hash"
	"io"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

type HashResult struct {
	Algorithm string
	Hash      string
	Duration  time.Duration
}

type FileHasher struct {
	FilePath string
	FileSize int64
	Results  []HashResult
}

func calculateHash(filepath string, hashType string, wg *sync.WaitGroup, results chan<- HashResult) {
	defer wg.Done()

	var h hash.Hash

	switch strings.ToLower(hashType) {
	case "md5":
		h = md5.New()
	case "sha1":
		h = sha1.New()
	case "sha256":
		h = sha256.New()
	case "sha512":
		h = sha512.New()
	default:
		return
	}

	start := time.Now()

	file, err := os.Open(filepath)
	if err != nil {
		results <- HashResult{Algorithm: hashType, Hash: "ERROR", Duration: 0}
		return
	}
	defer file.Close()

	if _, err := io.Copy(h, file); err != nil {
		results <- HashResult{Algorithm: hashType, Hash: "ERROR", Duration: 0}
		return
	}

	hashSum := hex.EncodeToString(h.Sum(nil))
	duration := time.Since(start)

	results <- HashResult{
		Algorithm: strings.ToUpper(hashType),
		Hash:      hashSum,
		Duration:  duration,
	}
}

func hashFile(filepath string, algorithms []string) (*FileHasher, error) {
	fileInfo, err := os.Stat(filepath)
	if err != nil {
		return nil, err
	}

	hasher := &FileHasher{
		FilePath: filepath,
		FileSize: fileInfo.Size(),
		Results:  make([]HashResult, 0),
	}

	results := make(chan HashResult, len(algorithms))
	var wg sync.WaitGroup

	for _, algo := range algorithms {
		wg.Add(1)
		go calculateHash(filepath, algo, &wg, results)
	}

	go func() {
		wg.Wait()
		close(results)
	}()

	for result := range results {
		hasher.Results = append(hasher.Results, result)
	}

	return hasher, nil
}

func formatSize(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.2f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

func printResults(hasher *FileHasher, verbose bool) {
	fmt.Printf("╔═══════════════════════════════════════════════════════════════════════╗\n")
	fmt.Printf("║                          Hash Calculator                              ║\n")
	fmt.Printf("╚═══════════════════════════════════════════════════════════════════════╝\n\n")

	fmt.Printf("File:     %s\n", filepath.Base(hasher.FilePath))
	if verbose {
		fmt.Printf("Path:     %s\n", hasher.FilePath)
	}
	fmt.Printf("Size:     %s (%d bytes)\n\n", formatSize(hasher.FileSize), hasher.FileSize)

	fmt.Printf("═══════════════════════════════════════════════════════════════════════\n")
	fmt.Printf("Hash Results:\n")
	fmt.Printf("═══════════════════════════════════════════════════════════════════════\n\n")

	for _, result := range hasher.Results {
		if result.Hash == "ERROR" {
			fmt.Printf("%-8s: ERROR\n", result.Algorithm)
		} else {
			fmt.Printf("%-8s: %s", result.Algorithm, result.Hash)
			if verbose {
				fmt.Printf(" (%v)", result.Duration)
			}
			fmt.Println()
		}
	}

	if verbose {
		fmt.Println()
		totalDuration := time.Duration(0)
		for _, result := range hasher.Results {
			totalDuration += result.Duration
		}
		fmt.Printf("Total computation time: %v\n", totalDuration)
		fmt.Printf("Parallel workers: %d\n", runtime.NumCPU())
	}
}

func main() {
	filePath := flag.String("file", "", "File to hash (required)")
	algorithms := flag.String("algo", "md5,sha1,sha256,sha512", "Comma-separated hash algorithms")
	verbose := flag.Bool("v", false, "Verbose output")
	output := flag.String("o", "", "Output file for results")
	verify := flag.String("verify", "", "Verify hash against expected value (format: algo:hash)")

	flag.Parse()

	if *filePath == "" {
		fmt.Println("Error: file path is required")
		fmt.Println("\nUsage:")
		flag.PrintDefaults()
		fmt.Println("\nExamples:")
		fmt.Println("  hashcalc -file document.pdf")
		fmt.Println("  hashcalc -file image.jpg -algo md5,sha256")
		fmt.Println("  hashcalc -file file.zip -verify sha256:abc123...")
		fmt.Println("  hashcalc -file data.bin -v -o hashes.txt")
		os.Exit(1)
	}

	algoList := strings.Split(*algorithms, ",")
	for i, algo := range algoList {
		algoList[i] = strings.TrimSpace(algo)
	}

	hasher, err := hashFile(*filePath, algoList)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	printResults(hasher, *verbose)

	if *verify != "" {
		parts := strings.SplitN(*verify, ":", 2)
		if len(parts) != 2 {
			fmt.Println("\nError: verify format should be algo:hash")
			os.Exit(1)
		}

		verifyAlgo := strings.ToUpper(strings.TrimSpace(parts[0]))
		verifyHash := strings.ToLower(strings.TrimSpace(parts[1]))

		fmt.Println()
		fmt.Printf("═══════════════════════════════════════════════════════════════════════\n")
		fmt.Printf("Verification:\n")
		fmt.Printf("═══════════════════════════════════════════════════════════════════════\n")

		found := false
		for _, result := range hasher.Results {
			if result.Algorithm == verifyAlgo {
				found = true
				if strings.ToLower(result.Hash) == verifyHash {
					fmt.Printf("✓ %s hash matches!\n", verifyAlgo)
				} else {
					fmt.Printf("✗ %s hash does NOT match!\n", verifyAlgo)
					fmt.Printf("  Expected: %s\n", verifyHash)
					fmt.Printf("  Got:      %s\n", strings.ToLower(result.Hash))
					os.Exit(1)
				}
				break
			}
		}

		if !found {
			fmt.Printf("✗ Algorithm %s was not computed\n", verifyAlgo)
			os.Exit(1)
		}
	}

	if *output != "" {
		file, err := os.Create(*output)
		if err != nil {
			fmt.Fprintf(os.Stderr, "\nError creating output file: %v\n", err)
			os.Exit(1)
		}
		defer file.Close()

		fmt.Fprintf(file, "File: %s\n", hasher.FilePath)
		fmt.Fprintf(file, "Size: %s (%d bytes)\n\n", formatSize(hasher.FileSize), hasher.FileSize)

		for _, result := range hasher.Results {
			if result.Hash != "ERROR" {
				fmt.Fprintf(file, "%s: %s\n", result.Algorithm, result.Hash)
			}
		}

		fmt.Printf("\n✓ Results saved to: %s\n", *output)
	}
}
