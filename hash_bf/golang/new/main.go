package main

// please do not use it for bad purposes!

import (
	"crypto/md5"
	"crypto/sha1"
	"crypto/sha256"
	"crypto/sha512"
	"encoding/hex"
	"flag"
	"fmt"
	"runtime"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

type HashFunction func([]byte) string

var (
	hashFunctions = map[string]HashFunction{
		"1": func(data []byte) string {
			hash := md5.Sum(data)
			return hex.EncodeToString(hash[:])
		},
		"2": func(data []byte) string {
			hash := sha1.Sum(data)
			return hex.EncodeToString(hash[:])
		},
		"3": func(data []byte) string {
			hash := sha256.Sum256(data)
			return hex.EncodeToString(hash[:])
		},
		"4": func(data []byte) string {
			hash := sha512.Sum512(data)
			return hex.EncodeToString(hash[:])
		},
	}

	charsets = map[string]string{
		"1": "0123456789",
		"2": "abcdefghijklmnopqrstuvwxyz",
		"3": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
		"4": " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~",
	}
)

func worker(id int, targetHash string, hashFunc HashFunction, charset string,
	combinations []string, resultChan chan<- string, wg *sync.WaitGroup,
	attempts *int64, startTime time.Time, found *int32) {

	defer wg.Done()

	for _, candidate := range combinations {
		if atomic.LoadInt32(found) == 1 {
			return
		}

		currentAttempts := atomic.AddInt64(attempts, 1)

		if currentAttempts%50000 == 0 {
			elapsed := time.Since(startTime).Seconds()
			if elapsed > 0 {
				rate := float64(currentAttempts) / elapsed
				fmt.Printf("[Worker %d] Attempts: %d, Rate: %.0f/s\n",
					id, currentAttempts, rate)
			}
		}

		candidateHash := hashFunc([]byte(candidate))

		if candidateHash == targetHash {
			if atomic.CompareAndSwapInt32(found, 0, 1) {
				resultChan <- candidate
			}
			return
		}
	}
}

func ParallelBruteForce(targetHash string, hashFunc HashFunction,
	charset string, maxLen int, numWorkers int) (string, int64, time.Duration) {

	var attempts int64
	var found int32
	startTime := time.Now()
	resultChan := make(chan string, 1)

	if numWorkers <= 0 {
		numWorkers = runtime.NumCPU()
		if numWorkers > 16 {
			numWorkers = 16
		}
	}

	fmt.Printf("[+] Using %d workers (CPU cores: %d)\n", numWorkers, runtime.NumCPU())

	for length := 1; length <= maxLen; length++ {
		fmt.Printf("[+] Processing length %d...\n", length)

		totalCombinations := pow(len(charset), length)
		if totalCombinations == 0 {
			continue
		}

		workers := numWorkers
		if totalCombinations < numWorkers {
			workers = totalCombinations
		}

		combinationsPerWorker := totalCombinations / workers
		var wg sync.WaitGroup

		for w := 0; w < workers; w++ {
			start := w * combinationsPerWorker
			end := (w + 1) * combinationsPerWorker

			if w == workers-1 {
				end = totalCombinations
			}

			combinations := generateCombinations(charset, length, start, end)
			if len(combinations) == 0 {
				continue
			}

			wg.Add(1)
			go worker(w+1, targetHash, hashFunc, charset, combinations,
				resultChan, &wg, &attempts, startTime, &found)
		}

		wg.Wait()

		select {
		case result := <-resultChan:
			elapsed := time.Since(startTime)
			return result, atomic.LoadInt64(&attempts), elapsed
		default:
		}

		if atomic.LoadInt32(&found) == 1 {
			break
		}
	}

	elapsed := time.Since(startTime)
	return "", atomic.LoadInt64(&attempts), elapsed
}

func generateCombinations(charset string, length int, start, end int) []string {
	if start >= end || length <= 0 {
		return []string{}
	}

	total := len(charset)
	combinations := make([]string, 0, end-start)

	for idx := start; idx < end; idx++ {
		var builder strings.Builder
		builder.Grow(length)
		temp := idx

		for i := 0; i < length; i++ {
			builder.WriteByte(charset[temp%total])
			temp /= total
		}

		str := builder.String()
		runes := []rune(str)
		for i, j := 0, len(runes)-1; i < j; i, j = i+1, j-1 {
			runes[i], runes[j] = runes[j], runes[i]
		}

		combinations = append(combinations, string(runes))
	}

	return combinations
}

func SimpleParallelBruteForce(targetHash string, hashFunc HashFunction,
	charset string, maxLen int) (string, int64, time.Duration) {

	var found int32
	var attempts int64
	startTime := time.Now()
	resultChan := make(chan string, 1)

	done := make(chan bool)
	var once sync.Once
	closeDone := func() {
		once.Do(func() {
			close(done)
		})
	}

	searchLength := func(length int) {
		totalCombs := pow(len(charset), length)
		batchSize := 10000

		for start := 0; start < totalCombs; start += batchSize {
			select {
			case <-done:
				return
			default:
				end := start + batchSize
				if end > totalCombs {
					end = totalCombs
				}

				combinations := generateCombinations(charset, length, start, end)
				for _, candidate := range combinations {
					if atomic.LoadInt32(&found) == 1 {
						return
					}

					atomic.AddInt64(&attempts, 1)

					if atomic.LoadInt64(&attempts)%100000 == 0 {
						elapsed := time.Since(startTime).Seconds()
						if elapsed > 0 {
							rate := float64(atomic.LoadInt64(&attempts)) / elapsed
							fmt.Printf("[Progress] Attempts: %d, Rate: %.0f/s\n",
								atomic.LoadInt64(&attempts), rate)
						}
					}

					candidateHash := hashFunc([]byte(candidate))
					if candidateHash == targetHash {
						if atomic.CompareAndSwapInt32(&found, 0, 1) {
							resultChan <- candidate
							closeDone()
						}
						return
					}
				}
			}
		}
	}

	for length := 1; length <= maxLen; length++ {
		go searchLength(length)
	}

	timeout := time.After(5 * time.Minute)
	select {
	case result := <-resultChan:
		closeDone()
		elapsed := time.Since(startTime)
		return result, atomic.LoadInt64(&attempts), elapsed
	case <-timeout:
		closeDone()
		elapsed := time.Since(startTime)
		return "", atomic.LoadInt64(&attempts), elapsed
	}
}

func main() {
	var (
		targetHash  string
		hashAlgo    string
		maxLen      int
		charsetType string
		workers     int
		mode        string
	)

	flag.StringVar(&targetHash, "hash", "", "Target hash to crack")
	flag.StringVar(&hashAlgo, "algo", "1", "Hash algorithm (1=MD5, 2=SHA1, 3=SHA256, 4=SHA512)")
	flag.IntVar(&maxLen, "len", 5, "Maximum password length")
	flag.StringVar(&charsetType, "charset", "1", "Charset (1=digits, 2=lowercase, 3=alphanum, 4=all)")
	flag.IntVar(&workers, "workers", 0, "Number of workers (0=auto)")
	flag.StringVar(&mode, "mode", "simple", "Mode (simple or advanced)")
	flag.Parse()

	if targetHash == "" {
		fmt.Println("=== Parallel Hash Brute Force (Go) ===")
		fmt.Print("\nEnter target hash: ")
		fmt.Scanln(&targetHash)

		if targetHash == "" {
			targetHash = "5d41402abc4b2a76b9719d911017c592"
			hashAlgo = "1"
			maxLen = 5
			charsetType = "3"
			mode = "simple"
		}
	}

	targetHash = strings.ToLower(strings.TrimSpace(targetHash))

	hashFunc, exists := hashFunctions[hashAlgo]
	if !exists {
		hashFunc = hashFunctions["1"]
	}

	charset, exists := charsets[charsetType]
	if !exists {
		charset = charsets["1"]
	}

	fmt.Printf("\n[+] Target hash: %s\n", targetHash)
	fmt.Printf("[+] Charset: %d symbols\n", len(charset))
	fmt.Printf("[+] Max length: %d\n", maxLen)

	totalCombs := 0
	for i := 1; i <= maxLen; i++ {
		totalCombs += pow(len(charset), i)
	}
	fmt.Printf("[+] Total combinations: %d\n", totalCombs)

	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("[+] Starting brute force...")

	var password string
	var attempts int64
	var elapsed time.Duration

	if mode == "advanced" {
		password, attempts, elapsed = ParallelBruteForce(targetHash, hashFunc, charset, maxLen, workers)
	} else {
		password, attempts, elapsed = SimpleParallelBruteForce(targetHash, hashFunc, charset, maxLen)
	}

	fmt.Println("\n" + strings.Repeat("=", 60))
	if password != "" {
		fmt.Printf("[+] SUCCESS! Password: '%s'\n", password)
		fmt.Printf("[+] Hash verified: %s\n", hashFunc([]byte(password)))
	} else {
		fmt.Println("[-] Password not found")
	}

	fmt.Printf("[+] Total attempts: %d\n", attempts)
	fmt.Printf("[+] Time elapsed: %v\n", elapsed)
	if elapsed.Seconds() > 0 {
		rate := float64(attempts) / elapsed.Seconds()
		fmt.Printf("[+] Speed: %.0f attempts/second\n", rate)
		if totalCombs > 0 {
			coverage := float64(attempts) / float64(totalCombs) * 100
			fmt.Printf("[+] Coverage: %.2f%%\n", coverage)
		}
	}
	fmt.Println(strings.Repeat("=", 60))
}

func pow(base, exponent int) int {
	if exponent == 0 {
		return 1
	}
	result := 1
	for i := 0; i < exponent; i++ {
		result *= base
	}
	return result
}
