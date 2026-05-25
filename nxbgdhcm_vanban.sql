-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: May 25, 2026 at 05:29 AM
-- Server version: 12.2.2-MariaDB
-- PHP Version: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `nxbgdhcm_vanban`
--

-- --------------------------------------------------------

--
-- Table structure for table `aia_chat_layer_0`
--

CREATE TABLE `aia_chat_layer_0` (
  `chat_id` bigint(20) NOT NULL COMMENT 'Mã cuộc hội thoại (Khóa chính)',
  `Person_key` varchar(255) NOT NULL COMMENT 'Chủ sở hữu',
  `chat_title` varchar(255) DEFAULT 'Hội thoại mới' COMMENT 'Tên cuộc hội thoại hiển thị Sidebar',
  `chat_sum_counter` int(11) DEFAULT 0 COMMENT 'Đếm số tin nhắn chưa tóm tắt',
  `chat_total_messages` int(11) DEFAULT 0 COMMENT 'Tổng số tin nhắn thực tế của hội thoại',
  `chat_summary` text DEFAULT NULL COMMENT 'Tóm tắt bối cảnh (Dưới 2000 chữ)',
  `chat_datasheet` text DEFAULT NULL COMMENT 'Sổ lưu số liệu: Key = Value Unit; (Tối đa 5000 chữ)',
  `created_at` datetime DEFAULT current_timestamp() COMMENT 'Giờ tạo',
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Giờ có tin nhắn mới nhất'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `aia_chat_layer_1`
--

CREATE TABLE `aia_chat_layer_1` (
  `chat_l1_id` bigint(20) NOT NULL,
  `chat_id` bigint(20) NOT NULL COMMENT 'Liên kết với bảng Layer 0',
  `role` varchar(20) NOT NULL COMMENT 'user, assistant, system',
  `content` longtext NOT NULL COMMENT 'Nội dung tin nhắn',
  `summared` tinyint(1) DEFAULT 0 COMMENT '0: Chưa tóm tắt, 1: Đã đưa vào summary',
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `cau_hinh`
--

CREATE TABLE `cau_hinh` (
  `Person_key` varchar(255) NOT NULL,
  `Key_Name` varchar(255) NOT NULL,
  `Value` text DEFAULT NULL,
  `Description` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `cau_hinh_prompt`
--

CREATE TABLE `cau_hinh_prompt` (
  `Prompt_Key` varchar(50) NOT NULL COMMENT 'Khóa định danh câu lệnh prompt',
  `Prompt_Content` text NOT NULL COMMENT 'Nội dung câu lệnh mẫu gửi cho AI',
  `prompt_type` varchar(50) NOT NULL DEFAULT 'in_app' COMMENT 'Phân loại môi trường sử dụng',
  `Description` varchar(255) DEFAULT NULL COMMENT 'Mô tả chi tiết công dụng'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `deleted_documents`
--

CREATE TABLE `deleted_documents` (
  `md5` varchar(255) NOT NULL,
  `person_key` varchar(255) NOT NULL,
  `file_name` text DEFAULT NULL,
  `file_path` text DEFAULT NULL,
  `file_type` varchar(50) DEFAULT NULL,
  `doc_type` varchar(255) DEFAULT NULL,
  `doc_number` varchar(255) DEFAULT NULL,
  `doc_day` varchar(10) DEFAULT NULL,
  `doc_month` varchar(10) DEFAULT NULL,
  `doc_year` varchar(10) DEFAULT NULL,
  `doc_org` text DEFAULT NULL,
  `doc_signer` text DEFAULT NULL,
  `full_text` longtext DEFAULT NULL,
  `deleted_time` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `documents`
--

CREATE TABLE `documents` (
  `md5` varchar(255) NOT NULL,
  `person_key` varchar(255) NOT NULL,
  `file_name` text DEFAULT NULL,
  `file_path` text DEFAULT NULL,
  `file_type` varchar(50) DEFAULT NULL,
  `doc_type` varchar(255) DEFAULT NULL,
  `doc_number` varchar(255) DEFAULT NULL,
  `doc_day` varchar(10) DEFAULT NULL,
  `doc_month` varchar(10) DEFAULT NULL,
  `doc_year` varchar(10) DEFAULT NULL,
  `doc_org` text DEFAULT NULL,
  `doc_signer` text DEFAULT NULL,
  `full_text` longtext DEFAULT NULL,
  `summary` text DEFAULT NULL,
  `last_scan` bigint(20) DEFAULT NULL,
  `Fixed` tinyint(4) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `ket_noi_ai`
--

CREATE TABLE `ket_noi_ai` (
  `ID` int(11) NOT NULL,
  `person_key` varchar(255) DEFAULT NULL,
  `Preset_Name` varchar(255) DEFAULT NULL,
  `URL` varchar(500) DEFAULT NULL,
  `Model_Name` varchar(100) DEFAULT NULL,
  `API_Key` varchar(255) DEFAULT NULL,
  `Default` varchar(10) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `lich_su_ten_file`
--

CREATE TABLE `lich_su_ten_file` (
  `ID` int(11) NOT NULL,
  `Person_key` varchar(255) DEFAULT NULL,
  `MD5` varchar(255) DEFAULT NULL,
  `File_Path` text DEFAULT NULL,
  `Ten_Hien_Tai` text DEFAULT NULL,
  `Ten_Cu` text DEFAULT NULL,
  `Thoi_Diem` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `loai_van_ban`
--

CREATE TABLE `loai_van_ban` (
  `ID` int(11) NOT NULL,
  `Loai_VB` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `Mo_ta` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Tu_khoa` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `nguoi_dung`
--

CREATE TABLE `nguoi_dung` (
  `Person_key` varchar(255) NOT NULL,
  `Mac_Address` varchar(100) DEFAULT NULL,
  `Computer_Name` varchar(255) DEFAULT NULL,
  `User_Name` varchar(255) DEFAULT NULL,
  `danh_xung` varchar(11) DEFAULT NULL,
  `Ho_Va_Ten` varchar(255) DEFAULT '',
  `Chuc_vu` varchar(255) DEFAULT '',
  `Phong_Ban` varchar(255) DEFAULT '',
  `Cong_tac` text DEFAULT NULL COMMENT 'Công việc đang được phân công',
  `NV_Phong` text DEFAULT NULL COMMENT 'Nhiệm vụ được giao của phòng',
  `Chuc_danh_khac` text DEFAULT NULL COMMENT 'Các chức danh kiêm nhiệm',
  `SYLL` longtext DEFAULT NULL COMMENT 'Sơ yếu lý lịch/Thông tin chi tiết'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tach_file`
--

CREATE TABLE `tach_file` (
  `MD5` varchar(255) NOT NULL,
  `Trang` int(11) NOT NULL,
  `Toan_van` longtext DEFAULT NULL,
  `Nhan_xet` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tao_van_ban`
--

CREATE TABLE `tao_van_ban` (
  `ID` int(11) NOT NULL,
  `Person_key` varchar(255) NOT NULL,
  `thoi_gian` datetime DEFAULT current_timestamp(),
  `ten_van_ban` varchar(500) DEFAULT NULL,
  `noi_dung` longtext DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `van_ban_mau`
--

CREATE TABLE `van_ban_mau` (
  `id` int(11) NOT NULL,
  `Loai_Van_Ban` varchar(255) NOT NULL COMMENT 'Tên loại văn bản (vd: Tờ trình, Công văn, Hợp đồng)',
  `Ung_Dung` text DEFAULT NULL COMMENT 'Sơ lược về công dụng và trường hợp sử dụng',
  `Mo_Ta_Layout` longtext DEFAULT NULL COMMENT 'Mô tả chi tiết bố cục và cách trình bày bằng mã HTML',
  `Thanh_Phan_Tat_Yeu` text DEFAULT NULL COMMENT 'Danh sách các thông tin cần có, phân cách bằng dấu chấm phẩy',
  `Phòng_Ban_So_Huu` varchar(100) DEFAULT NULL COMMENT 'Phòng ban chịu trách nhiệm về mẫu này',
  `Ngay_Cap_Nhat` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `aia_chat_layer_0`
--
ALTER TABLE `aia_chat_layer_0`
  ADD PRIMARY KEY (`chat_id`),
  ADD KEY `idx_person_updated` (`Person_key`,`updated_at`) COMMENT 'Index giúp truy xuất Sidebar cực nhanh';

--
-- Indexes for table `aia_chat_layer_1`
--
ALTER TABLE `aia_chat_layer_1`
  ADD PRIMARY KEY (`chat_l1_id`),
  ADD KEY `idx_chat_created` (`chat_id`,`created_at`);

--
-- Indexes for table `cau_hinh`
--
ALTER TABLE `cau_hinh`
  ADD PRIMARY KEY (`Person_key`,`Key_Name`);

--
-- Indexes for table `cau_hinh_prompt`
--
ALTER TABLE `cau_hinh_prompt`
  ADD PRIMARY KEY (`Prompt_Key`);

--
-- Indexes for table `deleted_documents`
--
ALTER TABLE `deleted_documents`
  ADD PRIMARY KEY (`md5`,`person_key`);

--
-- Indexes for table `documents`
--
ALTER TABLE `documents`
  ADD PRIMARY KEY (`md5`,`person_key`);
ALTER TABLE `documents` ADD FULLTEXT KEY `full_text` (`full_text`);

--
-- Indexes for table `ket_noi_ai`
--
ALTER TABLE `ket_noi_ai`
  ADD PRIMARY KEY (`ID`);

--
-- Indexes for table `lich_su_ten_file`
--
ALTER TABLE `lich_su_ten_file`
  ADD PRIMARY KEY (`ID`);

--
-- Indexes for table `loai_van_ban`
--
ALTER TABLE `loai_van_ban`
  ADD PRIMARY KEY (`ID`);

--
-- Indexes for table `nguoi_dung`
--
ALTER TABLE `nguoi_dung`
  ADD PRIMARY KEY (`Person_key`);

--
-- Indexes for table `tach_file`
--
ALTER TABLE `tach_file`
  ADD PRIMARY KEY (`MD5`,`Trang`);

--
-- Indexes for table `tao_van_ban`
--
ALTER TABLE `tao_van_ban`
  ADD PRIMARY KEY (`ID`);
ALTER TABLE `tao_van_ban` ADD FULLTEXT KEY `ten_van_ban` (`ten_van_ban`,`noi_dung`);

--
-- Indexes for table `van_ban_mau`
--
ALTER TABLE `van_ban_mau`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `aia_chat_layer_0`
--
ALTER TABLE `aia_chat_layer_0`
  MODIFY `chat_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'Mã cuộc hội thoại (Khóa chính)';

--
-- AUTO_INCREMENT for table `aia_chat_layer_1`
--
ALTER TABLE `aia_chat_layer_1`
  MODIFY `chat_l1_id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `ket_noi_ai`
--
ALTER TABLE `ket_noi_ai`
  MODIFY `ID` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `lich_su_ten_file`
--
ALTER TABLE `lich_su_ten_file`
  MODIFY `ID` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `loai_van_ban`
--
ALTER TABLE `loai_van_ban`
  MODIFY `ID` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `tao_van_ban`
--
ALTER TABLE `tao_van_ban`
  MODIFY `ID` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `van_ban_mau`
--
ALTER TABLE `van_ban_mau`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `aia_chat_layer_1`
--
ALTER TABLE `aia_chat_layer_1`
  ADD CONSTRAINT `fk_chat_layer_0` FOREIGN KEY (`chat_id`) REFERENCES `aia_chat_layer_0` (`chat_id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
